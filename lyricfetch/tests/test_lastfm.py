import asyncio

import pytest
from httpx import HTTPStatusError

from lyricfetch.lastfm import get_lastfm as _get_lastfm


def get_lastfm(*args, **kwargs):
    return asyncio.run(_get_lastfm(*args, **kwargs))


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
    with pytest.raises(HTTPStatusError):
        get_lastfm('track.getInfo', lastfm_key='asdfasdf')


def test_get_lastfm_wrong_method(lastfm_key):
    """
    `get_lastfm` should fail if the method requested is invalid.
    """
    with pytest.raises(HTTPStatusError):
        get_lastfm('asdfasdf', lastfm_key=lastfm_key)


def test_get_lastfm_wrong_arguments(lastfm_key):
    """
    `get_lastfm` should fail and return an empty string if they arguments to
    the method are invalid.
    """
    empty = get_lastfm('track.getInfo', lastfm_key=lastfm_key,
                       asdfasdf='asdfasdf')
    assert empty is None
