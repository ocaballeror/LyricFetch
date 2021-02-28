"""
Tests for the specific scraping functions.
"""
import asyncio
from http.client import RemoteDisconnected

import pytest
from httpx import HTTPStatusError

from lyricfetch import Song
from lyricfetch import exclude_sources
from lyricfetch import sources
from lyricfetch.scraping import azlyrics, metrolyrics, lyricswikia
from lyricfetch.scraping import darklyrics, metalarchives, genius
from lyricfetch.scraping import musixmatch, songlyrics, vagalume
from lyricfetch.scraping import letras, lyricsmode, lyricscom
from lyricfetch.scraping import get_url as _get_url
from lyricfetch.scraping import id_source
from lyricfetch.scraping import normalize


def check_site_available(site, secure=False):
    """
    Helper function to check if a specific website is available.
    """
    if not isinstance(site, str):
        url = id_source(site, full=True).lower()
    else:
        url = site
    if not url.startswith('http'):
        prefix = 'https' if secure else 'http'
        url = f'{prefix}://{url}'

    try:
        get_url(url, parser='raw')
    except HTTPStatusError:
        return False
    except RemoteDisconnected:
        if secure:
            return False
        return check_site_available(site, secure=True)
    return True


def get_url(*args, **kwargs):
    return asyncio.run(_get_url(*args, **kwargs))


def test_get_url():
    """
    Check that `get_url` returns the contents of a url using different parsers.
    """
    test_site = 'http://example.com'
    if not check_site_available(test_site):
        pytest.skip('Test site not available')

    soup = get_url(test_site, parser='html')
    assert soup
    assert soup.get_text().strip() != ''
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')

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
    test_site = 'http://www.metal-archives.com'
    if not check_site_available(test_site):
        pytest.skip('Test site not available')

    soup = get_url(test_site, parser='html')
    assert soup
    assert hasattr(soup, 'html')
    assert hasattr(soup, 'head')
    assert hasattr(soup, 'body')
    assert soup.get_text() != ''


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
        name = id_source(source)
        assert isinstance(name, str)
        assert name != ''
        name = id_source(source, full=True)
        assert isinstance(name, str)
        assert name != ''


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
    assert newlist == sources[-1:]


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
    try:
        lyrics = site(song)
    except RemoteDisconnected:
        pytest.skip('Remote disconnected')
    assert lyrics != ''


@pytest.mark.parametrize('artist,title', [
    ('anthrax', 'i am the law'),
])
def test_scrape_darklyrics(artist, title, lastfm_key):
    """
    Test scraping darklyrics, whose banning policy requires some special checks
    to be performed.
    """
    extra_check = 'www.darklyrics.com/j/judaspriest/painkiller.html'
    if not check_site_available(extra_check):
        pytest.skip('Darklyrics blocked you again')
    song = Song(artist=artist, title=title)
    try:
        lyrics = darklyrics(song)
    except RemoteDisconnected:
        pytest.skip('Remote disconnected')
    assert lyrics != ''
