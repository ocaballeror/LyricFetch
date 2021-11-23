"""
Common fixtures and helper functions.
"""
import os
import shutil
import tempfile
import urllib.request
from contextlib import contextmanager

import pytest
import eyed3
from jeepney_objects import DBusObject

from lyricfetch import CONFIG


@pytest.fixture(scope='session')
def _mp3file():
    """
    A helper to mp3file() with a session scope, so we don't download the same
    file everytime the fixture is invoked.
    """
    filename = tempfile.mktemp()
    url = 'http://www.noiseaddicts.com/samples_1w72b820/4930.mp3'
    urllib.request.urlretrieve(url, filename=filename)
    assert os.stat(filename).st_size > 0
    audiofile = eyed3.load(filename)
    audiofile.tag = eyed3.id3.Tag()
    audiofile.tag.save()

    yield filename
    if os.path.isfile(filename):
        os.unlink(filename)


@pytest.fixture
def mp3file(_mp3file):
    """
    A sample, valid mp3 file downloaded from the internet.
    """
    file_copy = tempfile.mktemp()
    shutil.copy(_mp3file, file_copy)
    yield file_copy
    if os.path.isfile(file_copy):
        os.unlink(file_copy)


@pytest.fixture
def lastfm_key():
    key = CONFIG['lastfm_key']
    if not key:
        pytest.skip('No lastfm key configured')
    return key


def tag_mp3(filename, **kwargs):
    """
    Write the specified tags to an mp3 file.
    """
    audiofile = eyed3.load(filename)
    for key, arg in kwargs.items():
        if key == 'lyrics':
            audiofile.tag.lyrics.set(arg)
        else:
            setattr(audiofile.tag, key, arg)
    audiofile.tag.save()


@contextmanager
def chdir(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


@pytest.fixture
def dbus_service(request):
    service = DBusObject()
    try:
        service.request_name(request.param)
    except RuntimeError:
        pytest.skip("Can't get the requested name")

    try:
        yield service
    finally:
        service.stop()
