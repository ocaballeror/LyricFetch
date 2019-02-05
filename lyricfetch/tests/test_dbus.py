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
from jeepney.wrappers import new_error

from lyricfetch.song import Song
from lyricfetch.song import get_current_amarok
from lyricfetch.song import get_current_cmus
from lyricfetch.song import get_current_spotify

from sample_responses import sample_response_amarok
from sample_responses import sample_response_cmus
from sample_responses import sample_response_spotify


class DBusInterface:
    def __init__(self):
        self.methods = {}
        self.properties = {}

    def __repr__(self):
        return f'Methods: {self.methods}, Properties: {self.properties}'


class DBusObject:
    def __init__(self):
        self.name = None
        self.interfaces = defaultdict(DBusInterface)
        self.stop = False
        self.conn = connect_and_authenticate(bus='SESSION')
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

    def set_handler(self, path, method_name, handler, interface=None):
        addr = (path, interface)
        self.interfaces[addr].methods[method_name] = handler

    def get_handler(self, path, method_name, interface=None):
        addr = (path, interface)
        if interface is None:
            method = self.interfaces[addr].methods.get(method_name, None)
            if method:
                return method
            for i_addr, iface in self.interfaces.items():
                if i_addr[0] == path and method_name in iface.methods:
                    return iface.methods[method_name]
        else:
            if method_name in self.interfaces[addr].methods:
                return self.interfaces[addr].methods[method_name]
        raise KeyError(f"Unregistered method '{method_name}'")

    def set_property(self, path, prop_name, signature, value, interface=None):
        addr = (path, interface)
        self.interfaces[addr].properties[prop_name] = (signature, value)

    def get_property(self, path, prop_name, interface=None):
        addr = (path, interface)
        if prop_name not in self.interfaces[addr].properties:
            err = f"Property '{prop_name}' not registered on this interface"
            raise KeyError(err)

        signature, value = self.interfaces[addr].properties[prop_name]
        return signature, value

    def _listen(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        while True:
            self.conn.recv_messages()

    def listen(self):
        self.listen_process.start()

    def stop(self):
        self.listen_process.terminate()

    def _handle_property_msg(self, msg):
        hdr = msg.header
        path = hdr.fields[HeaderFields.path]
        method = hdr.fields[HeaderFields.member]
        iface = msg.body[0]
        if method == 'Get':
            try:
                _, prop_name = msg.body
                signature, value = self.get_property(path, prop_name, iface)
                return new_method_return(msg, signature, value)
            except KeyError as error:
                return new_error(msg, 'KeyError', signature='s',
                                 body=(str(error),))
        elif method == 'Set':
            _, prop_name, (signature, value) = msg.body
            self.set_property(path, prop_name, signature, value, iface)
        elif method == 'GetAll':
            try:
                properties = self.get_all_properties(path, iface)
                return new_method_return(msg, 'a{sv}', properties)
            except KeyError as error:
                return new_error(msg, 'KeyError', signature='s',
                                 body=(str(error),))

        return None

    def _handle_method_call(self, msg):
        hdr = msg.header
        path = hdr.fields[HeaderFields.path]
        method = hdr.fields[HeaderFields.member]
        iface = hdr.fields.get(HeaderFields.interface, None)
        try:
            method = self.get_handler(path, method, iface)
            signature, body = method()
            return new_method_return(msg, signature, body)
        except Exception as error:
            return new_error(msg, str(error), signature='s',
                             body=(str(error), ))

        return None

    def handle_msg(self, msg):
        hdr = msg.header
        if not hdr.message_type == MessageType.method_call:
            return

        iface = hdr.fields.get(HeaderFields.interface, None)
        if iface == 'org.freedesktop.DBus.Properties':
            response = self._handle_property_msg(msg)
        else:
            response = self._handle_method_call(msg)

        if isinstance(response, Message):
            msg_type = response.header.message_type
            if msg_type in (MessageType.method_return, MessageType.error):
                sender = msg.header.fields[HeaderFields.sender]
                response.header.fields[HeaderFields.destination] = sender
                response.header.fields[HeaderFields.sender] = self.name
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

    service = DBusObject()
    try:
        service.request_name('org.kde.amarok')
    except RuntimeError:
        pytest.skip("Can't get the requested name")

    service.set_handler('/Player', 'GetMetadata', reply_msg)
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

    service = DBusObject()
    try:
        service.request_name('org.mpris.MediaPlayer2.spotify')
    except RuntimeError:
        pytest.skip("Can't get the requested name")

    service.set_handler('/org/mpris/MediaPlayer2', 'Get', get_property)
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
