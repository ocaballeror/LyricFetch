"""
Tests for the specific scraping functions.
"""
import sys
import urllib.request
from urllib.error import URLError
from http.client import RemoteDisconnected

import pytest

from conftest import lastfm_key

from lyrics import Song
from lyrics import id_source
from lyrics import get_url
from lyrics import azlyrics, metrolyrics, lyricswikia
from lyrics import darklyrics, metalarchives, genius
from lyrics import musixmatch, songlyrics, vagalume
from lyrics import letras, lyricsmode, lyricscom


def check_site_available(site, secure=False):
    print('sup')
    try:
        url = id_source(site, full=True).lower()
        prefix = 'https' if secure else 'http'
        print(url)
        get_url(f'{prefix}://{url}', parser='raw')
    except URLError as error:
        if secure:
            print(type(error), error)
            return False
        return check_site_available(site, secure=True)
    except RemoteDisconnected:
        return False
    return True


@pytest.mark.parametrize('site,artist,title',
    [
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
    ]
)
def test_scrap(site, artist, title):
    """
    Test all the scraping methods, each of which should return a set of lyrics
    for a known-to-be-found song.
    """
    lastfm_key()
    if not check_site_available(site):
        pytest.skip('This site is not avialable')
    song = Song.from_info(artist=artist, title=title)
    lyrics = site(song)
    assert lyrics != ''
