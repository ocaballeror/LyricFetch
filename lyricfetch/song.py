import os
from pathlib import Path

import eyed3

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
