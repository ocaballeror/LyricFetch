"""
Tests for the specific scraping functions.
"""
from urllib.error import URLError
from http.client import RemoteDisconnected

import pytest

from conftest import lastfm_key
from lyricfetch import Song
from lyricfetch import id_source
from lyricfetch import azlyrics, metrolyrics, lyricswikia
from lyricfetch import darklyrics, metalarchives, genius
from lyricfetch import musixmatch, songlyrics, vagalume
from lyricfetch import letras, lyricsmode, lyricscom
from lyricfetch.lyrics import get_url


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


@pytest.mark.parametrize('site,artist,title', [
    (azlyrics, 'slayer', 'live undead'),
    (darklyrics, 'anthrax', 'i am the law'),
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
def test_scrap(site, artist, title):
    """
    Test all the scraping methods, each of which should return a set of lyrics
    for a known-to-be-found song.
    """
    if not check_site_available(site):
        pytest.skip('This site is not avialable')
    if site is darklyrics:
        lastfm_key()
        extra_check = 'www.darklyrics.com/j/judaspriest/painkiller.html'
        if not check_site_available(extra_check):
            pytest.skip('Darklyrics blocked you again')
    song = Song.from_info(artist=artist, title=title)
    lyrics = site(song)
    assert lyrics != ''
