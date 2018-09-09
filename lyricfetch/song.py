"""
Module containing the representation of a song object, and a few extra methods
to get the current playing song.
"""
import os
import subprocess
from pathlib import Path

import eyed3
import dbus
from dbus.exceptions import DBusException

from . import logger
from .scraping import get_lastfm


class Song:
    """
    Representation of a song object.

    It contains the basic metadata (artist, title) and optionally the lyrics,
    album and filepath to the corresponding mp3 if applicable.

    Instead of the typical constructor, one of the 3 classmethods should be use
    to create a song object. Either from_filename, from_info or from_string
    depending on the use case.
    """
    def __init__(self, artist='', title='', album='', lyrics=''):
        self.artist = artist
        self.title = title
        self.album = album
        self.lyrics = lyrics

    def __repr__(self):
        items = self.__dict__.copy()
        del items['lyrics']
        values = ('='.join((k, v)) for k, v in items.items() if v)
        return 'Song({})'.format(', '.join(values))

    def __str__(self):
        if hasattr(self, 'filename'):
            return self.filename
        elif self.artist and self.title:
            return f'{self.artist.title()} - {self.title.title()}'
        else:
            return ''

    def __eq__(self, other):
        if hasattr(self, 'filename') and hasattr(other, 'filename'):
            return Path(self.filename) == Path(other.filename)
        else:
            equal = self.artist.lower() == other.artist.lower()
            equal = equal and self.title.lower() == other.title.lower()
            return equal

    def __hash__(self):
        if hasattr(self, 'filename'):
            return hash(self.filename)
        return hash((self.artist, self.title, self.album))

    @classmethod
    def from_filename(cls, filename):
        """
        Class constructor using the path to the corresponding mp3 file. The
        metadata will be read from this file to create the song object, so it
        must at least contain valid ID3 tags for artist and title.
        """
        if not filename:
            logger.error('No filename specified')
            return None

        if not os.path.exists(filename):
            logger.error("Err: File '%s' does not exist", filename)
            return None

        if os.path.isdir(filename):
            logger.error("Err: File '%s' is a directory", filename)
            return None

        try:
            audiofile = eyed3.load(filename)
        except Exception as error:
            print(type(error), error)
            return None

        # Sometimes eyed3 may return a null object and not raise any exceptions
        if audiofile is None:
            return None

        tags = audiofile.tag
        album = tags.album
        title = tags.title
        lyrics = ''.join([l.text for l in tags.lyrics])
        artist = tags.album_artist
        if not artist:
            artist = tags.artist

        song = cls(artist, title, album, lyrics)
        song.filename = filename
        return song

    @classmethod
    def from_string(cls, name, separator='-', reverse=False):
        """
        Class constructor using a string with the artist and title. This should
        be used when parsing user input, since all the information must be
        specified in a single string formatted as: '{artist} - {title}'.
        """
        recv = [t.strip() for t in name.split(separator)]
        if len(recv) < 2:
            logger.error('Wrong format!')
            return None

        if reverse:
            title = recv[0]
            artist = ''.join(recv[1:])
        else:
            artist = recv[0]
            title = ''.join(recv[1:])

        if not artist or not title:
            logger.error('Wrong format!')
            return None

        song = cls(artist, title)
        return song

    def fetch_album_name(self):
        """
        Get the name of the album from lastfm.
        """
        response = get_lastfm('track.getInfo', artist=self.artist,
                              track=self.title)
        if response:
            try:
                self.album = response['track']['album']['title']
                logger.debug('Found album %s from lastfm', self.album)
            except Exception:
                logger.warning('Could not fetch album name for %s', self)
        else:
            logger.warning('Could not fetch album name for %s', self)


def get_dbus_object(bus_name, path):
    """
    Return a dbus object from the specified path and bus name.
    """
    # List object paths with 'qdbus <bus_name>'
    # List methods with 'qdbus <bus_name> <path>'
    bus = dbus.SessionBus()
    return bus.get_object(bus_name, path)


def get_info_mpris2(name):
    """
    Get the current playing song from an mpris2 compliant player.
    """
    # qdbus org.mpris.MediaPlayer2.<name> /org/mpris/MediaPlayer2\
    # org.freedesktop.DBus.Properties.Get org.mpris.MediaPlayer2.Player Metadat
    bus_name = 'org.mpris.MediaPlayer2.' + name
    path = '/org/mpris/MediaPlayer2'
    player = get_dbus_object(bus_name, path)
    iface = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
    metadata = iface.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
    keys = ['album', 'title', 'artist', 'albumartist']

    info = {}
    metadata = {k: v for k, v in metadata.items() if 'xesam:' in k}
    for key, value in metadata.items():
        name = key.split(':')[1].lower()
        if name not in keys or name in info:
            continue
        if isinstance(value, dbus.Array):
            value = value[0]
        info[name] = value

    if 'albumartist' in info:
        info['artist'] = info['albumartist']
        del info['albumartist']

    return Song(**info)


def get_current_amarok():
    """
    Get the current song from amarok.
    """
    player = get_dbus_object('org.kde.amarok', '/Player')
    metadata = player.GetMetadata()
    return Song(metadata['artist'], metadata['title'], metadata['album'])


def get_current_clementine():
    """
    Get the current song from clementine.
    """
    # mpris_version 2
    try:
        return get_info_mpris2('clementine')
    except DBusException:
        bus_name = 'org.mpris.clementine'
        path = '/Player'
        player = get_dbus_object(bus_name, path)

        iface_name = 'org.freedesktop.MediaPlayer'
        iface = dbus.Interface(player, dbus_interface=iface_name)
        metadata = iface.GetMetadata()
        return Song(metadata['artist'], metadata['title'], metadata['album'])

    else:
        return get_info_mpris2('clementine')


def get_current_cmus():
    """
    Get the current song from cmus.
    """
    result = subprocess.run('cmus-remote -Q'.split(' '), check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    info = {}
    for line in result.stdout.decode().split('\n'):
        line = line.split(' ')
        if line[0] != 'tag':
            continue
        key = line[1]
        if key in ['album', 'title', 'artist', 'albumartist'] and\
           key not in info:
            info[key] = ' '.join(line[2:])

    if 'albumartist' in info:
        info['artist'] = info['albumartist']
        del info['albumartist']

    return Song(**info)


def get_current_spotify():
    """
    Get the current song from spotify.
    """
    return get_info_mpris2('spotify')


probers = {
    'amarok': get_current_amarok,
    'clementine': get_current_clementine,
    'cmus': get_current_cmus,
    'spotify': get_current_spotify
}


def get_current_song():
    """
    Try all the known players and return the "Now playing" information of
    the first available one.
    """
    for func in probers.values():
        try:
            return func()
        except Exception:
            pass
    return None
