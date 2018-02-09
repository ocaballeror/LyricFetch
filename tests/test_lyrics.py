"""
Main tests module.
"""
import pytest
import sys

sys.path.append('..')
from lyrics import get_soup


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
    pass


def test_get_lastfm():
    """
    The `get_lastfm` function should return a json object with the response
    from the method requested.
    """
    pass


def test_get_lastfm_wrong_key():
    """
    `get_lastfm` should fail and return an empty string if they key is invalid.
    """
    pass


def test_get_lastfm_wrong_method():
    """
    `get_lastfm` should fail and return an empty string if the method requested
    is invalid.
    """
    pass


def test_normalize():
    """
    Check that normalize removes extraneous characters from the passed string.
    """
    pass


def test_normalize_extra_chars_dir():
    """
    Check that normalize removes from the string the extra characters passed in
    a dictionary.
    """
    pass


def test_normalize_extra_chars_string():
    """
    Check that normalize removes from the string the extra characters passed as
    a string.
    """
    pass


def test_id_source_mappings():
    """
    Check that every source function has a mapping in `id_source`, and none of
    them return an empty string.
    """
    pass


def test_exclude_sources():
    """
    Check that sources are correctly excluded from the main list if the method
    is called before a run.
    """
    pass


def test_getlyrics():
    """
    Check that the main method can actually return a result with lyrics.
    """
    pass


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


