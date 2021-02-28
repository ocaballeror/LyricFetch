"""
Tests for the `Song` class.
"""
import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from tempfile import TemporaryDirectory

from conftest import tag_mp3
from lyricfetch import Song


def test_song_from_filename(mp3file):
    """
    Create a song object from an mp3 file.
    """
    tag_mp3(mp3file,
            artist='Kataklysm',
            title='Born to kill and destined to die',
            album='Meditations')

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

    with NamedTemporaryFile() as temp:
        assert Song.from_filename(temp.name) is None

    with TemporaryDirectory() as temp:
        assert Song.from_filename(temp) is None


def test_song_init():
    """
    Create a song object with a set of parameters.
    """
    song = Song('Opeth', 'Bleak', 'Blackwater Park')
    assert song
    assert song.artist == 'Opeth'
    assert song.title == 'Bleak'
    assert song.album == 'Blackwater Park'
    assert song.lyrics == ''
    assert not hasattr(song, 'filename')


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
    def fetch_album(song):
        asyncio.run(song.fetch_album_name())

    song = Song(artist='Barren earth', title='The living fortress')
    assert song.album == ''
    fetch_album(song)
    assert song.album.lower() == 'a complex of cages'

    song = Song(artist='Dropkick Murphys', title='asdfasdfasdf')
    fetch_album(song)
    assert song.album == ''


def test_song_eq_different_class():
    """
    Compare a song object to things that are not Song objects.
    """
    class FakeSong:
        pass

    class DaughterSong(Song):
        pass

    song = Song('beyond the dawn', 'deathstar')
    assert song is not None

    fake_song = FakeSong()
    fake_song.artist = song.artist
    fake_song.title = song.title
    assert song != fake_song

    daughter = DaughterSong(song.artist, song.title)
    assert song == daughter


def test_song_eq_filename():
    """
    Check that song comparison turns out equal when they point to the same file
    name.
    """
    song = Song("Be'lakor", 'Renmants')
    othersong = Song('Carnation', 'Hatred Unleashed')

    song.filename = 'song1.mp3'
    othersong.filename = song.filename
    assert song == othersong
    othersong.filename = Path(song.filename)
    assert song == othersong

    othersong.artist = song.artist
    othersong.title = song.title
    othersong.filename = song.filename + '_nope'
    assert song != othersong


def test_song_eq_attributes():
    """
    Compare two songs based on their attributes.
    """
    song = Song('Ordos', 'House of the dead')
    othersong = Song('Dvne', 'The Crimson Path')
    assert song != othersong

    othersong = Song('ordos', 'house OF THE DEAD')
    assert song == othersong

    othersong.album = 'House of the dead'
    assert song != othersong
