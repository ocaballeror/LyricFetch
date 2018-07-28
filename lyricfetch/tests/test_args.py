"""
Module to test the different CLI arguments that can be passed.
"""
import json
import os
import random
import shutil
import sys
import tempfile
from tempfile import NamedTemporaryFile
from argparse import ArgumentError
from pathlib import Path

import pytest
from py.path import local as pypath
from conftest import chdir
from conftest import tag_mp3

from lyricfetch import Song
from lyricfetch import lyrics
from lyricfetch.lyrics import CONFIG
from lyricfetch.lyrics import load_config
from lyricfetch.lyrics import load_from_file
from lyricfetch.lyrics import main
from lyricfetch.lyrics import parse_argv


@pytest.mark.parametrize('arg,config,klass', [
    ('-j', 'jobcount', int),
    ('--jobs', 'jobcount', int),
])
def test_argv_param(monkeypatch, arg, config, klass):
    """
    Test the arguments that accept a parameter and store it CONFIG.
    """
    new_argv = ['python', __file__, arg]
    if klass is int:
        param = random.randint(1, 10)
    new_argv.append(str(param))

    print(new_argv)
    monkeypatch.setattr(sys, 'argv', new_argv)
    parse_argv()
    assert CONFIG[config] == param


@pytest.mark.parametrize('arg,config', [
    ('-o', 'overwrite'),
    ('--overwrite', 'overwrite'),
    ('-s', 'print_stats',),
    ('--stats', 'print_stats',),
])
def test_argv_flag(monkeypatch, arg, config):
    """
    Test the arguments that work as flags, and set an attribute of CONFIG to
    True.
    """
    new_argv = ['python', __file__, arg]
    monkeypatch.setattr(sys, 'argv', new_argv)
    parse_argv()
    assert CONFIG[config]


@pytest.mark.parametrize('num', [-1, 0])
def test_argv_invalid_jobs(monkeypatch, num):
    """
    Check that `parse_argv()` raises some kind of error when an invalid number
    of jobs is passed.
    """
    new_argv = ['python', __file__, '-j', str(num)]

    current_value = CONFIG['jobcount']
    monkeypatch.setattr(sys, 'argv', new_argv)
    with pytest.raises(ValueError):
        parse_argv()
    assert CONFIG['jobcount'] == current_value



def test_argv_recursive(monkeypatch, mp3file):
    """
    Check that the `-r` flag searches recursively for mp3 files and returns a
    list with all the names found.
    """
    tmpdir = Path(tempfile.mkdtemp())
    tempdir_dir = tmpdir / 'dir'
    tempdir_dir.mkdir()
    mp3s = [
        tmpdir / 'first.mp3',
        tmpdir / 'second.mp3',
        tempdir_dir / 'third.mp3',
        tempdir_dir / 'fourth.mp3',
    ]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)

    monkeypatch.setattr(sys, 'argv', [__file__, '-r'])
    with chdir(str(tmpdir)):
        songs = parse_argv()
        songs = set(Path(s.filename).absolute() for s in songs)
    try:
        assert set(mp3s) == songs
    finally:
        shutil.rmtree(tmpdir)


def test_argv_recursive_path(monkeypatch, mp3file, tmpdir):
    """
    Check that the `-r` flag can search in a different path given as an
    argument too.
    """
    tempdir_dir = tmpdir / 'dir'
    tempdir_dir.mkdir()
    mp3s = [
        tmpdir / 'first.mp3',
        tmpdir / 'second.mp3',
        tempdir_dir / 'third.mp3',
        tempdir_dir / 'fourth.mp3',
    ]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)

    monkeypatch.setattr(sys, 'argv', [__file__, '-r', str(tmpdir)])
    songs = parse_argv()
    songs = set(pypath(s.filename) for s in songs)
    assert set(mp3s) == songs


def test_argv_by_name(monkeypatch):
    """
    Check that the `-n` flag accepts a song or list of songs by name, and
    returns a list of song objects with the information it parsed.
    """
    # Run it first with only one song
    artist, title = 'judas priest', 'no surrender'
    new_args = [__file__, '-n', f'{artist} - {title}']
    param_song = Song.from_info(artist, title)
    monkeypatch.setattr(sys, 'argv', new_args)
    songs = parse_argv()
    assert songs == set([param_song])

    # Then try with multiple songs
    param_songs = [
        Song.from_info('kreator', 'mars mantra'),
        Song.from_info('nervosa', 'morbid courage'),
        Song.from_info('ac/dc', 'night prowler'),
    ]
    new_args = [__file__, '-n']
    for p_song in param_songs:
        new_args.append(f'{p_song.artist} - {p_song.title}')
    monkeypatch.setattr(sys, 'argv', new_args)
    songs = parse_argv()
    assert songs == set(param_songs)


def test_argv_from_file(monkeypatch, tmpdir, mp3file):
    """
    Check that the `--from_file` argument can read a text file containing a
    list of filenames, and return a list with all of them.
    """
    mp3_files = [
        tmpdir / 'first.mp3',
        tmpdir / 'second.mp3',
        tmpdir / 'third.mp3',
    ]
    song_tags = [
        ('white wizzard', 'the sun also rises'),
        ('mastodon', 'andromeda'),
        ('megadeth', 'dawn patrol'),
    ]
    songs = []
    for filename, tag in zip(mp3_files, song_tags):
        artist, title = tag
        shutil.copyfile(mp3file, filename)
        tag_mp3(filename, artist=artist, title=title)
        songs.append(Song.from_info(artist=artist, title=title))

    with NamedTemporaryFile('w') as tmp:
        for filename in mp3_files:
            tmp.write(str(filename) + '\n')
        tmp.flush()

        monkeypatch.setattr(sys, 'argv', [__file__, '--from-file', tmp.name])
        parsed_songs = parse_argv()

    assert parsed_songs == set(parsed_songs)


def test_argv_filename(monkeypatch, mp3file, tmpdir):
    """
    Test that the main script can accept a list of file names passed as
    parameters, and return them all in a list.
    """
    mp3s = [
        tmpdir / 'first.mp3',
        tmpdir / 'second.mp3',
        tmpdir / 'third.mp3',
    ]
    new_args = [__file__]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)
        new_args.append(str(mp3))

    monkeypatch.setattr(sys, 'argv', new_args)
    songs = parse_argv()
    songs = set(pypath(s.filename) for s in songs)
    assert set(mp3s) == songs


@pytest.mark.parametrize('args', [
    ['-r', '-n'],
    ['-r', '--from-file'],
    ['-n', '--from-file'],
    ['-r', '-n', '--from-file'],
])
def test_argv_incompatible(monkeypatch, args):
    """
    Check that the `parse_argv` function raises some kind of error when these
    incompatible arguments are passed at the same time.
    """
    new_args = [__file__] + args
    monkeypatch.setattr(sys, 'argv', new_args)
    with pytest.raises(SystemExit):
        parse_argv()


def test_load_config(monkeypatch):
    """
    Test the `load_config()` function, which should read a json config file and
    update the CONFIG global dictionary accordingly.
    """
    config_dummy = {'test': True, 'othertest': 'stuff'}
    with NamedTemporaryFile('w') as tmp:
        tmp.write(json.dumps(config_dummy))
        tmp.flush()

        monkeypatch.setattr(lyrics, 'CONFFILE', tmp.name)
        load_config()
        assert 'test' in CONFIG
        assert 'othertest' in CONFIG
        assert CONFIG['test'] == config_dummy['test']
        assert CONFIG['othertest'] == config_dummy['othertest']


def test_load_from_file_errors(tmpdir):
    """
    Test the errors that can be raised from `load_from_file()`.
    """
    assert load_from_file(tmpdir) is None

    tmpdir.remove()
    assert load_from_file(tmpdir) is None

    with NamedTemporaryFile('w') as tmp:
        assert not load_from_file(tmp.name)


def test_main_errors(monkeypatch):
    """
    Test the different error conditions that can occurr when calling `main()`.
    """
    def empty_set():
        return set()

    def filled_set():
        return set('hello world')

    def value_error():
        raise ValueError('whattup')

    def fake_run(songs):
        raise KeyboardInterrupt

    # Make parse_argv() return an empty set
    monkeypatch.setattr(lyrics, 'parse_argv', empty_set)
    assert main() == 1

    # Make parse_argv() raise a ValueError
    monkeypatch.setattr(lyrics, 'parse_argv', value_error)
    assert main() == 1

    # Interrupt the process with a keyboard interrupt
    monkeypatch.setattr(lyrics, 'parse_argv', filled_set)
    monkeypatch.setattr(lyrics, 'run', fake_run)
    assert main() == 1
