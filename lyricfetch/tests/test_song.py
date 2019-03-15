"""
Tests for the `Song` class.
"""
from tempfile import NamedTemporaryFile
from tempfile import TemporaryDirectory

from lyricfetch import Song

from .conftest import tag_mp3


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
    # Empty filename
    assert Song.from_filename('') is None

    # Invalid mp3 file
    with NamedTemporaryFile() as temp:
        assert Song.from_filename(temp.name) is None

    # Inexistent file
    assert Song.from_filename(temp.name) is None

    # Directory
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
    song = Song(artist='Barren earth', title='The living fortress')
    assert song.album == ''
    song.fetch_album_name()
    assert song.album.lower() == 'a complex of cages'

    song = Song(artist='Dropkick Murphys', title='asdfasdfasdf')
    song.fetch_album_name()
    assert song.album == ''


def test_song_repr():
    """
    Test the song repr method, which should generate a valid song constructor
    statement.
    """
    song = Song('Allegaeon', 'All hail science', 'Proponent for sentience')
    song.lyrics = 'Some lyrics here'
    rep = repr(song).lower()

    assert 'song(' in rep
    assert 'artist="allegaeon"' in rep
    assert 'title="all hail science"' in rep
    assert 'album="proponent for sentience"' in rep
    assert 'lyrics' not in rep

    assert eval(repr(song)) == song


def test_song_str():
    """
    Test song conversion to str.
    """
    song = Song('First fragment', 'Dasein', 'Dasein')
    song.lyrics = 'Some lyrics here'
    rep = str(song).lower()

    assert rep == 'first fragment - dasein'

    song.filename = './song.mp3'
    assert str(song) == song.filename
