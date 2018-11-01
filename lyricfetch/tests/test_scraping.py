"""
Tests for the specific scraping functions.
"""
from urllib.error import URLError
from urllib.error import HTTPError
from http.client import RemoteDisconnected

import pytest

from conftest import lastfm_key
from lyricfetch import Song
from lyricfetch import id_source
from lyricfetch import azlyrics, metrolyrics, lyricswikia
from lyricfetch import darklyrics, metalarchives, genius
from lyricfetch import musixmatch, songlyrics, vagalume
from lyricfetch import letras, lyricsmode, lyricscom
from lyricfetch import exclude_sources
from lyricfetch import get_lastfm
from lyricfetch import sources
from lyricfetch.scraping import get_url
from lyricfetch.scraping import normalize


def check_site_available(site, secure=False):
    """
    Helper function to check if a specific website is available.
    """
    try:
        if not isinstance(site, str):
            url = id_source(site, full=True).lower()
        else:
            url = site
        prefix = 'https' if secure else 'http'
        get_url(f'{prefix}://{url}', parser='raw')
    except URLError as error:
        if secure:
            print(type(error), error)
            return False
        return check_site_available(site, secure=True)
    except RemoteDisconnected:
        return False
    return True


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


def test_exclude_sources_list_callable():
    """
    Check that sources are correctly excluded from the main list when passing a
    list of functions.
    """
    last_sources = sources[-2:]
    newlist = exclude_sources(last_sources)
    assert newlist == sources[:-2]


def test_exclude_sources_section_callable():
    """
    Check that sources are correctly excluded from the main list .
    """
    newlist = exclude_sources(sources[-2], section=True)
    assert newlist == sources[-2:]


@pytest.mark.parametrize('site,artist,title', [
    (azlyrics, 'slayer', 'live undead'),
    (genius, 'rammstein', 'rosenrot'),
    (letras, 'havok', 'afterburner'),
    (lyricscom, 'dark tranquillity', 'atom heart 243.5'),
    (lyricsmode, 'motorhead', 'like a nightmare'),
    (lyricswikia, 'in flames', 'everything counts'),
    (metalarchives, 'black sabbath', 'master of insanity'),
    (metrolyrics, 'flotsam and jetsam', 'fade to black'),
    (musixmatch, 'pantera', 'psycho holiday'),
    (songlyrics, 'sylosis', 'stained humanity'),
    (vagalume, 'epica', 'unchain utopia'),
])
def test_scrape(site, artist, title):
    """
    Test all the scraping methods, each of which should return a set of lyrics
    for a known-to-be-found song.
    """
    if not check_site_available(site):
        pytest.skip('This site is not available')
    song = Song(artist=artist, title=title)
    lyrics = site(song)
    assert lyrics != ''


@pytest.mark.parametrize('artist,title', [
    ('anthrax', 'i am the law'),
])
def test_scrape_darklyrics(artist, title):
    """
    Test scraping darklyrics, whose banning policy requires some special checks
    to be performed.
    """
    lastfm_key()
    extra_check = 'www.darklyrics.com/j/judaspriest/painkiller.html'
    if not check_site_available(extra_check):
        pytest.skip('Darklyrics blocked you again')
    song = Song(artist=artist, title=title)
    lyrics = darklyrics(song)
    assert lyrics != ''
