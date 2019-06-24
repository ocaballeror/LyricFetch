"""
Functions to test dbus-related functionality.
"""
import os
import sys

import pytest
from lyricfetch.song import Song
from lyricfetch.song import get_current_amarok
from lyricfetch.song import get_current_cmus
from lyricfetch.song import get_current_spotify
from lyricfetch.song import get_current_clementine

from sample_responses import sample_response_amarok
from sample_responses import sample_response_cmus
from sample_responses import sample_response_spotify
from sample_responses import sample_response_clementine


pytestmark = pytest.mark.skipif(
    sys.platform == 'win32', reason='DBus not supported on Windows'
)


@pytest.mark.parametrize('dbus_service', ['org.kde.amarok'], indirect=True)
def test_get_current_amarok(dbus_service):
    """
    Check that we can get the current song playing in amarok.
    """
    now_playing = Song(artist='Nightwish', title='Alpenglow',
                       album='Endless Forms Most Beautiful')

    dbus_service.set_handler('/Player', 'GetMetadata',
                             lambda: sample_response_amarok)
    dbus_service.listen()

    song = get_current_amarok()
    assert song == now_playing


@pytest.mark.parametrize('dbus_service,song,response,get_current', [
    ('org.mpris.MediaPlayer2.spotify',
     Song(artist='Gorod', title='Splinters of Life',
          album='Process of a new decline'),
     sample_response_spotify, get_current_spotify),
    ('org.mpris.MediaPlayer2.clementine',
     Song(artist='Rush', title='2112', album='2112'),
     sample_response_clementine, get_current_clementine),
], ids=['spotify', 'clementine'], indirect=['dbus_service'])
def test_get_current_spotify(dbus_service, song, response, get_current):
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
