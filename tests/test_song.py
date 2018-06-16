"""
Tests for the `Song` class.
"""
import os
import sys
import tempfile

import eyed3
import pytest

from test_lyrics import mp3file, lastfm_key

sys.path.append('..')
from lyrics import Song

def test_song_from_filename(mp3file):
    """
    Create a song object from an mp3 file.
    """
    audiofile = eyed3.load(mp3file)
    audiofile.tag.artist = 'Kataklysm'
    audiofile.tag.title = 'Born to kill and destined to die'
    audiofile.tag.album = 'Meditations'
    audiofile.tag.save()

    song = Song.from_filename(mp3file)
    assert song
    assert song.filename == mp3file
    assert song.artist == 'Kataklysm'
    assert song.title == 'Born to kill and destined to die'
    assert song.album == 'Meditations'


def test_song_from_filename_errors():
    """
    Test the different errors that may be raised from calling
    Song.from_filename().
    """
    assert Song.from_filename('') is None

    temp = tempfile.NamedTemporaryFile()
    os.unlink(temp.name)
    assert Song.from_filename(temp.name) is None

    temp = tempfile.TemporaryDirectory()
    assert Song.from_filename(temp.name) is None
    os.rmdir(temp.name)

def test_song_from_info():
    """
    Create a song object with a set of parameters.
    """
    song = Song.from_info('Opeth', 'Bleak', 'Blackwater Park')
    assert song
    assert song.artist == 'Opeth'
    assert song.title == 'Bleak'
    assert song.album == 'Blackwater Park'
    assert song.lyrics == ''
    assert not hasattr(song, 'filename')


def test_song_from_info_errors():
    """
    Test the different errors that may be raised from calling
    Song.from_info().
    """
    assert Song.from_info(artist='Annihilator', title='') is None
    assert Song.from_info(artist='', title='Locust Spawning') is None


def test_song_from_string():
    """
    Create a song object from an unparsed string.
    """
    song = Song.from_string('la marea - vetusta morla', reverse=True)
    assert song
    assert song.artist == 'vetusta morla'
    assert song.title == 'la marea'

    song = Song.from_string('els amics de les arts-ja no ens passa')
    assert song
    assert song.artist == 'els amics de les arts'
    assert song.title == 'ja no ens passa'

    song = Song.from_string('immolation / epiphany', separator='/')
    assert song
    assert song.artist == 'immolation'
    assert song.title == 'epiphany'


def test_song_from_string_errors():
    """
    Test the different errors that may be raised from calling
    Song.from_string().
    """
    assert Song.from_string('in flames versus terminus') is None
    assert Song.from_string('The sword -') is None
    assert Song.from_string('- Letterbomb') is None


def test_song_fetch_album_name(lastfm_key):
    """
    Check that a song can retrieve the album name if it's not given.
    """
    song = Song.from_info(artist='Barren earth', title='The living fortress')
    assert song.album == ''
    song.fetch_album_name()
    assert song.album.lower() == 'a complex of cages'

    song = Song.from_info(artist='Dropkick Murphys', title='asdfasdfasdf')
    song.fetch_album_name()
    assert song.album == ''
