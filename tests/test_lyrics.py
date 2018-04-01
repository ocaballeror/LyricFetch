"""
Main tests module.
"""
import pytest
import sys

sys.path.append('..')
from lyrics import get_soup
from lyrics import get_lastfm
from lyrics import normalize
from lyrics import sources
from lyrics import id_source
from lyrics import exclude_sources
from lyrics import Song
from lyrics import get_lyrics


def test_soup():
    """
    Check that `get_soup` returns a correct beautifulsoup object from a url.
    """
    soup = get_soup('http://example.com')
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')
    assert soup.get_text() != ""


def test_get_soup_tlsv1():
    """
    Check that `get_soup` can get data from a website using an older encryption
    protocol (TLSv1).
    """
    soup = get_soup('http://www.metal-archives.com')
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')
    assert soup.get_text() != ""


def test_get_lastfm():
    """
    The `get_lastfm` function should return a json object with the response
    from the method requested.
    """
    track = get_lastfm('track.getInfo', artist="Metallica", title="Master of"
                       "puppets")
    assert 'track' in track
    assert 'name' in track['track']
    assert 'artist' in track['track']
    assert 'album' in track['track']


def test_get_lastfm_wrong_key():
    """
    `get_lastfm` should fail and return an empty string if they key is invalid.
    """
    empty = get_lastfm('track.getInfo', asdfasdf='asdfasdf')
    assert empty == ''


def test_get_lastfm_wrong_method():
    """
    `get_lastfm` should fail and return an empty string if the method requested
    is invalid.
    """
    empty = get_lastfm('asdfasdf')
    assert empty == ''


def test_normalize():
    """
    Check that normalize removes extraneous characters from the passed string.
    """
    weird = 'aáeéiíoóöuúünñ'
    assert normalize(weird) == 'aeioun'


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
    assert normalize(weird, chars_dict) == '01ioun'


def test_normalize_extra_chars_string():
    """
    Check that normalize removes from the string the extra characters passed as
    a string.
    """
    weird = 'aáeéiíoóöuúünñ'
    assert normalize(weird, 'iou', '3') == 'ae333n'


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
    assert newlist + [last_source] == sources


def test_exclude_sources_str():
    """
    Check that a source is correctly excluded from the main list when passing
    the name of a function as a string.
    """
    last_source = sources[-1]
    newlist = exclude_sources(last_source.__name__)
    assert newlist + [last_source] == sources


def test_exclude_sources_list_callable():
    """
    Check that sources are correctly excluded from the main list when passing a
    list of functions.
    """
    last_sources = sources[-2:]
    newlist = exclude_sources(last_sources)
    assert newlist + last_sources == sources


def test_exclude_sources_list_str():
    """
    Check that sources are correctly excluded from the main list when passing a
    list of strings.
    """
    last_sources = sources[-2:]
    newlist = exclude_sources(map(lambda f: f.__name__, last_sources))
    assert newlist + last_sources == sources


def test_exclude_sources_section_callable():
    """
    Check that sources are correctly excluded from the main list .
    """
    second_to_last = sources[-2]
    newlist = exclude_sources(second_to_last, section=True)
    assert newlist == sources[-2:]


def test_exclude_sources_section_str():
    """
    Check that sources are correctly excluded from the main list .
    """
    second_to_last = sources[-2]
    newlist = exclude_sources(second_to_last.__name__, section=True)
    assert newlist == sources[-2:]


def test_getlyrics():
    """
    Check that the main method can actually return a result with lyrics.
    """
    song = Song.from_info(artist="Iron maiden", title="Hallowed be thy name")
    lyrics = get_lyrics(song)
    assert 'hallowed be thy name' in lyrics.lower()


def test_getlyrics_dont_overwrite():
    """
    Check that we skip a song if the mp3 file already has embedded lyrics.
    """
    pass


def test_getlyrics_overwrite():
    """
    Check that we can overwrite the lyrics of a song if it already has them.
    """
    pass
