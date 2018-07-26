"""
Common fixtures and helper functions.
"""
import json
import os
import sys
import urllib.request

import pytest
import eyed3


if '..' not in sys.path:
    sys.path.append('..')

from lyrics import CONFIG

CONFIG_FILE = '../config.json'


@pytest.fixture
def mp3file():
    """
    A sample, valid mp3 file downloaded from the internet.
    """
    url = 'http://www.noiseaddicts.com/samples_1w72b820/4930.mp3'
    filename, _ = urllib.request.urlretrieve(url)
    audiofile = eyed3.load(filename)
    audiofile.tag = eyed3.id3.Tag()
    audiofile.tag.save()
    yield filename
    os.unlink(filename)


@pytest.fixture(scope='session')
def lastfm_key():
    with open(CONFIG_FILE) as conffile:
        config = json.load(conffile)
        key = config['lastfm_key']
    if key == '':
        raise RuntimeError('No lastfm key configured')
    CONFIG['lastfm_key'] = key
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
