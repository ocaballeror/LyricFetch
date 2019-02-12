"""
Functions to test dbus-related functionality.
"""
import os

import pytest
import lyricfetch
from lyricfetch.song import Song
from lyricfetch.song import get_current_amarok
from lyricfetch.song import get_current_cmus
from lyricfetch.song import get_current_spotify
from lyricfetch.song import get_current_clementine
from lyricfetch.song import get_current_song

from sample_responses import sample_response_amarok
from sample_responses import sample_response_cmus
from sample_responses import sample_response_spotify
from sample_responses import sample_response_clementine


@pytest.mark.parametrize('dbus_service,path,iface,song,response,get_current', [
    ('org.kde.amarok', '/Player', '',
     Song('Nightwish', 'Alpenglow', 'Endless Forms Most Beautiful'),
     sample_response_amarok, get_current_amarok),
], ids=['amarok'], indirect=['dbus_service'])
def test_get_current_metadata(dbus_service, path, iface, song, response,
                              get_current):
    """
    Check that we can get the current song playing in amarok.
    """
    dbus_service.set_handler(path, 'GetMetadata', lambda: response,
                             interface=iface)
    dbus_service.listen()

    assert get_current() == song


@pytest.mark.parametrize('dbus_service,song,response,get_current', [
    ('org.mpris.MediaPlayer2.spotify',
     Song(artist='Gorod', title='Splinters of Life',
          album='Process of a new decline'),
     sample_response_spotify, get_current_spotify),
    ('org.mpris.MediaPlayer2.clementine',
     Song(artist='Rush', title='2112', album='2112'),
     sample_response_clementine, get_current_clementine),
], ids=['spotify', 'clementine'], indirect=['dbus_service'])
def test_get_current_mpris2(dbus_service, song, response, get_current):
    """
    Check that we can get the current song playing in amarok.
    """
    path = '/org/mpris/MediaPlayer2'
    interface = 'org.mpris.MediaPlayer2.Player'
    signature, value = response
    dbus_service.set_property(path, 'Metadata', signature, value, interface)
    dbus_service.listen()

    current = get_current()
    assert current == song


def test_get_current_cmus(monkeypatch, tmp_path):
    """
    Test that we can get the current song playing in cmus.
    """
    now_playing = Song(artist='Death', title='Baptized In Blood',
                       album='Scream Bloody Gore')
    # Create a fake cmus-remote script that will echo our response
    cmus = tmp_path / 'cmus-remote'
    contents = """\
#!/bin/sh
[ "$1" = "-Q" ] || exit 1
echo "{}"
    """
    contents = contents.format(sample_response_cmus)
    cmus.write_text(contents)

    # Make the script executable
    environ = os.environ.copy()
    environ['PATH'] = str(tmp_path) + ':' + environ['PATH']
    monkeypatch.setattr(os, 'environ', environ)
    os.chmod(cmus, 0o755)

    current = get_current_cmus()
    assert current
    assert current == now_playing


def test_get_current_song(monkeypatch):
    """
    Test the get_current_song function, which should query all the possible
    sources until one of them returns a valid answer.
    """
    def raise_error():
        raise Exception

    fake_probers = {
        'fault1': raise_error,
        'fault2': raise_error,
        'good1': lambda: 'good 1',
        'good2': lambda: 'good 2',
        'fault3': raise_error,
    }
    monkeypatch.setattr(lyricfetch.song, 'probers', fake_probers)
    assert get_current_song() == 'good 1'

    monkeypatch.setattr(lyricfetch.song, 'probers', {})
    assert get_current_song() is None
