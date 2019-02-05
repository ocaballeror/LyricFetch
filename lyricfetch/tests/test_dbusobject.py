from functools import partial

import pytest
from jeepney import DBusAddress
from jeepney.bus_messages import DBus
from jeepney.wrappers import new_method_call
from jeepney.wrappers import Properties
from jeepney.wrappers import DBusErrorResponse
from jeepney.integrate.blocking import connect_and_authenticate


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_basic_init(dbus_service):
    """
    Check that we can successfully initialize and register an object.
    """
    assert dbus_service

    conn = connect_and_authenticate()
    msg = DBus().NameHasOwner('com.example.object')
    response = conn.send_and_get_reply(msg)
    assert response == (1,)


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_object_method_call(dbus_service):
    """
    Register and call methods on a dbus object.
    """
    def str_response(body=''):
        return 's', (body, )

    interface = 'com.example.interface1'
    object_path = 'com.example.object'
    add0 = DBusAddress('/path', object_path)
    add1 = DBusAddress('/path/subpath', object_path)
    add2 = DBusAddress('/path', object_path, interface=interface)
    add3 = DBusAddress('/path/subpath', object_path, interface=interface)

    hello0 = partial(str_response, body='Hello0')
    hello1 = partial(str_response, body='Hello1')
    hello2 = partial(str_response, body='Hello2')
    hello3 = partial(str_response, body='Hello3')

    dbus_service.set_handler(add0.object_path, 'hello0', hello0)
    dbus_service.set_handler(add1.object_path, 'hello1', hello1)
    dbus_service.set_handler(add2.object_path, 'hello2', hello2, interface)
    dbus_service.set_handler(add3.object_path, 'hello3', hello3, interface)

    dbus_service.listen()
    conn = connect_and_authenticate()

    response = conn.send_and_get_reply(new_method_call(add0, 'hello0'))
    assert response == ('Hello0', )
    response = conn.send_and_get_reply(new_method_call(add1, 'hello1'))
    assert response == ('Hello1', )
    response = conn.send_and_get_reply(new_method_call(add2, 'hello2'))
    assert response == ('Hello2', )
    response = conn.send_and_get_reply(new_method_call(add3, 'hello3'))
    assert response == ('Hello3', )


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_object_wrong_method_call(dbus_service):
    """
    Try to call an inexistent method and verify that an error is returned.
    """
    object_path = 'com.example.object'
    addr = DBusAddress('/path', object_path)

    dbus_service.listen()
    conn = connect_and_authenticate()
    with pytest.raises(DBusErrorResponse):
        conn.send_and_get_reply(new_method_call(addr, 'some_method'))


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_object_get_property(dbus_service):
    """
    Set and get properties from a dbus object.
    """
    interface = 'com.example.interface1'
    object_path = 'com.example.object'
    add0 = DBusAddress('/path', object_path, interface=interface)
    add1 = DBusAddress('/path/subpath', object_path, interface=interface)

    dbus_service.set_property(add0.object_path, 'prop0', 's', ('hello0',),
                              add0.interface)
    dbus_service.set_property(add1.object_path, 'prop1', 's', ('hello1',),
                              add1.interface)

    dbus_service.listen()
    conn = connect_and_authenticate()

    response = conn.send_and_get_reply(Properties(add0).get('prop0'))
    assert response == ('hello0', )
    response = conn.send_and_get_reply(Properties(add1).get('prop1'))
    assert response == ('hello1', )


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_object_get_all_properties(dbus_service):
    """
    Get all properties from a dbus object.
    """
    interface = 'com.example.interface1'
    object_path = 'com.example.object'
    addr = DBusAddress('/path', object_path, interface=interface)

    dbus_service.set_property(addr.object_path, 'prop0', 's', 'hello0',
                              addr.interface)
    dbus_service.set_property(addr.object_path, 'prop1', 's', 'hello1',
                              addr.interface)
    dbus_service.set_property(addr.object_path, 'prop2', 's', 'hello2',
                              addr.interface)

    dbus_service.listen()
    conn = connect_and_authenticate()

    response = conn.send_and_get_reply(Properties(addr).get_all())
    assert response == ([('prop0', ('s', 'hello0')),
                         ('prop1', ('s', 'hello1')),
                         ('prop2', ('s', 'hello2'))], )


@pytest.mark.parametrize('dbus_service', ['com.example.object'], indirect=True)
def test_object_wrong_property(dbus_service):
    """
    Try to get an inexistent property and verify that an error is returned.
    """
    object_path = 'com.example.object'
    interface = 'com.example.interface1'
    addr = DBusAddress('/path', object_path, interface=interface)

    dbus_service.listen()
    conn = connect_and_authenticate()
    with pytest.raises(DBusErrorResponse):
        conn.send_and_get_reply(Properties(addr).get('prop'))
