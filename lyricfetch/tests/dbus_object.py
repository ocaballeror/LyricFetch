"""
This module contains the classes and methods to publish dbus objects.
"""
import asyncio

from collections import defaultdict
from multiprocessing import Process

from jeepney.low_level import HeaderFields
from jeepney.low_level import Message, MessageType
from jeepney.io.blocking import open_dbus_connection
from jeepney.bus_messages import DBus
from jeepney.wrappers import new_method_return
from jeepney.wrappers import new_error


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
        self.conn = open_dbus_connection(bus='SESSION')
        self.conn._unwrap_reply = True  # backwards compatible behavior
        self.conn.router.on_unhandled = self.handle_msg
        self.listen_process = None

    def request_name(self, name):
        dbus = DBus()
        reply = self.conn.send_and_get_reply(dbus.RequestName(name))
        if reply != (1,):
            raise RuntimeError("Couldn't get requested name")
        self.name = name

    def release_name(self):
        try:
            self.conn.send_message(DBus().ReleaseName(self.name))
        except OSError:
            # This probably means the name has already been released
            self.name = None
        except Exception as e:
            print('Error releasing name', type(e), e)
            raise
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

    def get_all_properties(self, path, interface):
        addr = (path, interface)
        return (list(self.interfaces[addr].properties.items()),)

    def _listen(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        while True:
            try:
                self.conn.recv_messages()
            except Exception:
                pass

    def listen(self):
        self.listen_process = Process(target=self._listen)
        self.listen_process.start()

    def stop(self):
        if self.name:
            try:
                self.release_name()
            except Exception:
                pass
        if self.listen_process and self.listen_process.is_alive():
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
