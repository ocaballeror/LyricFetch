"""
Main tests module.
"""
import shutil
import tempfile
import time
from urllib.error import HTTPError
from queue import Queue

import pytest

from conftest import tag_mp3
from lyricfetch import CONFIG
from lyricfetch import Result
from lyricfetch import Song
from lyricfetch import azlyrics
from lyricfetch import exclude_sources
from lyricfetch import get_lastfm
from lyricfetch import get_lyrics
from lyricfetch import id_source
from lyricfetch import lyrics
from lyricfetch.lyrics import LyrThread
from lyricfetch.lyrics import get_lyrics_threaded
from lyricfetch.lyrics import get_url
from lyricfetch.lyrics import normalize
from lyricfetch.lyrics import process_result
from lyricfetch.lyrics import run_mp
from lyricfetch.lyrics import sources


def test_get_url():
    """
    Check that `get_url` returns the contents of a url using different parsers.
    """
    soup = get_url('http://example.com', parser='html')
    assert soup
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')
    assert soup.get_text != ''

    raw = get_url('http://example.com', parser='raw')
    assert '<html>' in raw
    assert '<head>' in raw
    assert '<body>' in raw
    assert '</body>' in raw
    assert '</head>' in raw
    assert '</html>' in raw

    url = 'http://jsonapiplayground.reyesoft.com/v2/authors'
    json_response = get_url(url, parser='json')
    assert json_response
    assert isinstance(json_response, dict)
    assert 'data' in json_response


def test_get_url_tlsv1():
    """
    Check that `get_url` can get data from a website using an older encryption
    protocol (TLSv1).
    """
    soup = get_url('http://www.metal-archives.com')
    assert soup
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')
    assert soup.get_text() != ''


def test_get_lastfm(lastfm_key):
    """
    The `get_lastfm` function should return a json object with the response
    from the method requested.
    """
    track = get_lastfm('track.getInfo', lastfm_key=lastfm_key,
                       artist='Metallica', track='Master of puppets')
    assert 'track' in track
    assert 'name' in track['track']
    assert 'artist' in track['track']
    assert 'album' in track['track']


def test_get_lastfm_wrong_key():
    """
    `get_lastfm` should fail if they key is invalid.
    """
    with pytest.raises(HTTPError):
        get_lastfm('track.getInfo', lastfm_key='asdfasdf')


def test_get_lastfm_wrong_method(lastfm_key):
    """
    `get_lastfm` should fail if the method requested is invalid.
    """
    with pytest.raises(HTTPError):
        get_lastfm('asdfasdf', lastfm_key=lastfm_key)


def test_get_lastfm_wrong_arguments(lastfm_key):
    """
    `get_lastfm` should fail and return an empty string if they arguments to
    the method are invalid.
    """
    empty = get_lastfm('track.getInfo', lastfm_key=lastfm_key,
                       asdfasdf='asdfasdf')
    assert empty == ''


def test_normalize():
    """
    Check that normalize removes extraneous characters from the passed string.
    """
    weird = 'aáeéiíoóöuúünñ'
    assert normalize(weird) == 'aaeeiiooouuunn'


def test_normalize_extra_chars_dir():
    """
    Check that normalize removes from the string the extra characters passed in
    a dictionary.
    """
    chars_dict = {
        'a': '0',
        'e': '1'
    }
    weird = 'aáeéiíoóöuúünñ'
    assert normalize(weird, chars_dict) == '0011iiooouuunn'


def test_normalize_extra_chars_string():
    """
    Check that normalize removes from the string the extra characters passed as
    a string.
    """
    weird = 'aáeéiíoóöuúünñ'
    assert normalize(weird, 'o', '4') == 'aaeeii444uuunn'
    assert normalize(weird, 'iu', '3') == 'aaee33ooo333nn'
    assert normalize(weird, 'n', '99') == 'aaeeiiooouuu9999'


def test_id_source_mappings():
    """
    Check that every source function has a mapping in `id_source`, and none of
    them return an empty string.
    """
    for source in sources:
        assert id_source(source) != ''
        assert id_source(source, full=True) != ''


def test_exclude_sources_callable():
    """
    Check that a source is correctly excluded from the main list when passing a
    function.
    """
    last_source = sources[-1]
    newlist = exclude_sources(last_source)
    assert newlist == sources[:-1]


def test_exclude_sources_str():
    """
    Check that a source is correctly excluded from the main list when passing
    the name of a function as a string.
    """
    last_source = sources[-1]
    newlist = exclude_sources(last_source.__name__)
    assert newlist == sources[:-1]


def test_exclude_sources_list_callable():
    """
    Check that sources are correctly excluded from the main list when passing a
    list of functions.
    """
    last_sources = sources[-2:]
    newlist = exclude_sources(last_sources)
    assert newlist == sources[:-2]


def test_exclude_sources_list_str():
    """
    Check that sources are correctly excluded from the main list when passing a
    list of strings.
    """
    last_sources = list(map(lambda f: f.__name__, sources[-2:]))
    newlist = exclude_sources(last_sources)
    assert newlist == sources[:-2]


def test_exclude_sources_section_callable():
    """
    Check that sources are correctly excluded from the main list .
    """
    newlist = exclude_sources(sources[-2], section=True)
    assert newlist == sources[-2:]


def test_exclude_sources_section_str():
    """
    Check that sources are correctly excluded from the main list .
    """
    newlist = exclude_sources(sources[-2].__name__, section=True)
    assert newlist == sources[-2:]


def test_getlyrics_from_info():
    """
    Check that the main method can actually return a result with lyrics.
    """
    song = Song(artist='Iron maiden', title='Hallowed be thy name')
    result = get_lyrics(song)
    assert 'hallowed be thy name' in result.song.lyrics.lower()


def test_getlyrics_from_song(mp3file):
    """
    Check that the main method can find the lyrics for a song and write them as
    ID3 metadata.
    """
    tag_mp3(mp3file, artist='YOB', title='Our raw heart')
    song = Song.from_filename(mp3file)
    result = get_lyrics(song)
    assert 'my restless ghost' in result.song.lyrics.lower()


def test_getlyrics_dont_overwrite(mp3file):
    """
    Check that we skip a song if the mp3 file already has embedded lyrics.
    """
    placeholder = 'Some lyrics'
    tag_mp3(mp3file, lyrics=placeholder)

    song = Song.from_filename(mp3file)
    CONFIG['overwrite'] = False
    assert get_lyrics(song) is None
    assert song.lyrics == placeholder


def test_getlyrics_overwrite(mp3file):
    """
    Check that we can overwrite the lyrics of a song if it already has them.
    """
    placeholder = 'Some lyrics'
    tag_mp3(mp3file, artist='Baroness', title='Eula', lyrics=placeholder)

    song = Song.from_filename(mp3file)
    CONFIG['overwrite'] = True
    result = get_lyrics(song)
    assert result.song.lyrics != placeholder
    assert 'forget the taste of my own tongue' in result.song.lyrics.lower()


def test_lyrthread_run():
    """
    Test the run method for the LyrThread class, which should find the lyrics
    for a song and put the result in a Queue.
    """
    def raise_error(arg):
        print('thing')
        raise ConnectionError

    # First a normal run where the function actually returns some lyrics
    queue = Queue()
    song = Song(artist='Avenged sevenfold', title='Demons')
    lyr_thread = LyrThread(lambda f: 'Lyrics', song, queue)
    lyr_thread.start()
    result = queue.get()
    assert isinstance(result, dict)
    assert result['runtime'] > 0
    assert result['lyrics'] == 'Lyrics'

    # Now we test a run where some error is raised
    lyr_thread = LyrThread(raise_error, song, queue)
    lyr_thread.start()
    result = queue.get()
    assert isinstance(result, dict)
    assert result['runtime'] > 0
    assert result['lyrics'] == ''


def test_getlyrics_threaded():
    """
    Test the `get_lyrics_threaded()` function, which should launch a pool of
    processes to search for lyrics in all the available sources, and return the
    result from the first one that returns valid lyrics.
    """
    def source_1(_):
        time.sleep(1)
        return 'Lyrics 1'

    def source_2(_):
        return 'Lyrics 2'

    def source_3(_):
        return ''

    # source_2 is faster than source_1, so we should expect it to return lyrics
    # first, and source_1 to not even be in the result that's returned
    song = Song(artist='Slipknot', title='The virus of life')
    result = get_lyrics_threaded(song, l_sources=[source_1, source_2])
    assert song.lyrics == 'Lyrics 2'
    assert result.song.lyrics == 'Lyrics 2'
    assert result.source == source_2
    assert result.runtimes[source_2] < 1
    assert source_1 not in result.runtimes

    # Now we use source_3, which is faster than source_1, but doesn't return
    # any lyrics, so we expect the function to ignore that result and give us
    # the lyrics from source_1
    song = Song(artist='Power trip', title='Ruination')
    result = get_lyrics_threaded(song, l_sources=[source_1, source_3])
    assert song.lyrics == 'Lyrics 1'
    assert result.song.lyrics == 'Lyrics 1'
    assert result.source == source_1
    assert result.runtimes[source_3] < 1
    assert result.runtimes[source_1] >= 1

    # Lastly, we try only source_3, so we should expect the result to have no
    # lyrics, and its `source` attribute to be None.
    song = Song('Amon amarth', 'Back on northern shores')
    result = get_lyrics_threaded(song, l_sources=[source_3] * 4)
    assert song.lyrics == ''
    assert result.song.lyrics == ''
    assert result.source is None
    assert result.runtimes[source_3] < 1


def test_run_mp(monkeypatch):
    """
    Test `run_mp()`, which should concurrently search for the lyrics of a list
    of songs, source by source.
    """
    monkeypatch.setattr(lyrics, 'get_lyrics', fake_getlyrics_run_mp)

    # fake_getlyrics will return: None, a Result with 'random_source' and a
    # Result with `None` as source (i.e. the lyrics were not found).
    songs = [False, azlyrics, None]
    start_time = time.time()
    CONFIG['jobcount'] = len(songs)
    stats = run_mp(songs)
    assert time.time() - start_time < len(songs)

    stats = stats.calculate()
    assert stats['found'] == 1
    assert stats['notfound'] == 1


def test_process_result(mp3file):
    """
    Check that the `process_result()` function can write the lyrics to the
    corresponding mp3 and return wheter or not they were found.
    """
    artist = 'lör'
    title = 'requiem'
    song_lyrics = 'hello world'
    tag_mp3(mp3file, artist=artist, title=title)
    song = Song.from_filename(mp3file)
    song.lyrics = song_lyrics

    result_notfound = Result(song=song, source=None, runtimes={})
    assert not process_result(result_notfound)
    assert not Song.from_filename(mp3file).lyrics

    result_found = Result(song=song, source='whatever', runtimes={})
    assert process_result(result_found)
    assert Song.from_filename(mp3file).lyrics == song_lyrics


def test_run_one_song(mp3file, monkeypatch):
    """
    Test the run() function when passing a single song object. It should call
    get_lyrics_threaded to search for lyrics in all the sources at the same
    time.
    """
    song_lyrics = 'some lyrics here'

    def fake_getlyricsthreaded(songs):
        song.lyrics = song_lyrics
        return Result(song=song, source='whatever', runtimes={})

    song = Song.from_filename(mp3file)
    monkeypatch.setattr(lyrics, 'get_lyrics_threaded', fake_getlyricsthreaded)
    lyrics.run(song)
    assert Song.from_filename(mp3file).lyrics == song_lyrics


def test_run_multiple_songs(mp3file, monkeypatch):
    """
    Test the run() function when passing multiple songs. This time it should
    call run_mp() on the entire collection.
    """
    def fake_runmp(songs):
        for i, song in enumerate(songs):
            tag_mp3(song.filename, lyrics=f'lyrics{i}')

    other_mp3 = tempfile.mktemp()
    shutil.copy(mp3file, other_mp3)
    mp3files = [mp3file, other_mp3]
    songs = [Song.from_filename(f) for f in mp3files]
    monkeypatch.setattr(lyrics, 'run_mp', fake_runmp)
    lyrics.run(songs)
    for i, filename in enumerate(mp3files):
        assert Song.from_filename(filename).lyrics == f'lyrics{i}'


def fake_getlyrics_run_mp(source):
    """
    Convenience function to replace the standard `get_lyrics()` that is used by
    `test_run_mp()`.
    """
    time.sleep(1)
    if source is False:
        return None

    runtimes = {azlyrics: 1}
    song = Song(artist='breaking benjamin', title='i will not bow')
    return Result(song, source, runtimes)
