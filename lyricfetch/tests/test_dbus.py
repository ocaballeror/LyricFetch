"""
Functions to test dbus-related functionality.
"""
import asyncio
import warnings
from collections import defaultdict
from multiprocessing import Process

from jeepney.low_level import HeaderFields
from jeepney.low_level import Message, MessageType
from jeepney.integrate.blocking import connect_and_authenticate
from jeepney.bus_messages import DBus


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
