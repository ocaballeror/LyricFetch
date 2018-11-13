"""
Functions to test dbus-related functionality.
"""
import asyncio
import os
import warnings
from collections import defaultdict
from multiprocessing import Process

import pytest
from jeepney.low_level import HeaderFields
from jeepney.low_level import Message, MessageType
from jeepney.integrate.blocking import connect_and_authenticate
from jeepney.bus_messages import DBus
from jeepney.wrappers import new_method_return
from jeepney.wrappers import DBusErrorResponse

from lyricfetch.song import Song
from lyricfetch.song import get_current_amarok
from lyricfetch.song import get_current_cmus
from lyricfetch.song import get_current_spotify

from sample_responses import sample_response_amarok
from sample_responses import sample_response_cmus
from sample_responses import sample_response_spotify


class DBusService:
    def __init__(self):
        self.name = None
        self.stop = False
        self.conn = connect_and_authenticate(bus='SESSION')
        self.handlers = defaultdict(dict)
        self.conn.router.on_unhandled = self.handle_msg
        self.listen_process = Process(target=self._listen)

    def request_name(self, name):
        dbus = DBus()
        reply = self.conn.send_and_get_reply(dbus.RequestName(name))
        if reply != (1,):
            raise RuntimeError("Couldn't get requested name")
        self.name = name

    def release_name(self):
        if self.listen_process.is_alive():
            self.listen_process.terminate()

        reply = self.conn.send_and_get_reply(DBus().ReleaseName(self.name))
        if reply != (1,):
            warnings.warn('Error releasing name')
        else:
            self.name = None

    def install_handler(self, path, method_name, handler):
        self.handlers[path][method_name] = handler

    def _listen(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        while True:
            self.conn.recv_messages()

    def listen(self):
        self.listen_process.start()

    def stop(self):
        self.listen_process.terminate()

    def handle_msg(self, msg):
        hdr = msg.header
        if not hdr.message_type == MessageType.method_call:
            return

        path = hdr.fields[HeaderFields.path]
        method = hdr.fields[HeaderFields.member]
        if path not in self.handlers:
            return
        if method not in self.handlers[path]:
            return

        response = self.handlers[path][method](msg)
        if isinstance(response, Message):
            if response.header.message_type == MessageType.method_return:
                sender = msg.header.fields[HeaderFields.sender]
                response.header.fields[HeaderFields.destination] = sender
                return self.conn.send_message(response)
        return msg


def test_get_current_amarok():
    """
    Check that we can get the current song playing in amarok.
    """
    now_playing = Song(artist='Nightwish', title='Alpenglow',
                       album='Endless Forms Most Beautiful')

    def reply_msg(msg):
        body = sample_response_amarok
        return new_method_return(msg, signature='a{sv}', body=body)

    service = DBusService()
    try:
        service.request_name('org.kde.amarok')
    except DBusErrorResponse:
        pytest.skip("Can't get the requested name")

    service.install_handler('/Player', 'GetMetadata', reply_msg)
    try:
        service.listen()

        song = get_current_amarok()
        assert song == now_playing
    finally:
        if service.name:
            service.release_name()


def test_get_current_spotify():
    """
    Check that we can get the current song playing in amarok.
    """
    now_playing = Song(artist='Gorod', title='Splinters of Life',
                       album='Process of a new decline')

    def get_property(msg):
        body = sample_response_spotify
        interface = msg.header.fields.get(HeaderFields.interface, None)
        if interface == 'org.freedesktop.DBus.Properties':
            if msg.body == ('org.mpris.MediaPlayer2.Player', 'Metadata'):
                return new_method_return(msg, signature='v', body=body)

    service = DBusService()
    try:
        service.request_name('org.mpris.MediaPlayer2.spotify')
    except DBusErrorResponse:
        pytest.skip("Can't get the requested name")

    service.install_handler('/org/mpris/MediaPlayer2', 'Get', get_property)
    try:
        service.listen()

        song = get_current_spotify()
        assert song == now_playing
    finally:
        if service.name:
            service.release_name()


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
