"""
Module to test the different CLI arguments that can be passed.
"""
import os
import random
import shutil
import sys
import tempfile
from argparse import ArgumentError
from pathlib import Path

import pytest

from test_lyrics import mp3file

sys.path.append('..')
from lyrics import CONFIG
from lyrics import Song
from lyrics import parse_argv


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
    tempdir = Path(tempfile.mkdtemp(dir='.'))
    tempdir_dir = tempdir / 'dir'
    os.mkdir(tempdir_dir)
    mp3s = [
        tempdir / 'first.mp3',
        tempdir / 'second.mp3',
        tempdir_dir / 'third.mp3',
        tempdir_dir / 'fourth.mp3',
    ]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)

    monkeypatch.setattr(sys, 'argv', [__file__, '-r'])
    songs = parse_argv()
    songs = set(Path(s.filename) for s in songs)
    try:
        assert set(mp3s) == songs
    finally:
        shutil.rmtree(tempdir)


def test_argv_recursive_path(monkeypatch, mp3file):
    """
    Check that the `-r` flag can search in a different path given as an
    argument too.
    """
    tempdir = Path(tempfile.mkdtemp())
    tempdir_dir = tempdir / 'dir'
    os.mkdir(tempdir_dir)
    mp3s = [
        tempdir / 'first.mp3',
        tempdir / 'second.mp3',
        tempdir_dir / 'third.mp3',
        tempdir_dir / 'fourth.mp3',
    ]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)

    monkeypatch.setattr(sys, 'argv', [__file__, '-r', str(tempdir)])
    songs = parse_argv()
    songs = set(Path(s.filename) for s in songs)
    try:
        assert set(mp3s) == songs
    finally:
        shutil.rmtree(tempdir)


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


def test_argv_from_file(monkeypatch):
    """
    Check that the `--from_file` argument can read a text file containing a
    list of filenames, and return a list with all of them.
    """
    param_songs = [
        Song.from_info('white wizzard', 'the sun also rises'),
        Song.from_info('mastodon', 'andromeda'),
        Song.from_info('megadeth', 'dawn patrol'),
    ]
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        tmp_name = tmp.name
        for song in param_songs:
            tmp.write(f'{song.artist} - {song.title}\n')
        tmp.close()

    monkeypatch.setattr(sys, 'argv', [__file__, '--from-file', tmp_name])
    songs = parse_argv()
    assert songs == set(param_songs)


def test_argv_filename(monkeypatch, mp3file):
    """
    Test that the main script can accept a list of file names passed as
    parameters, and return them all in a list.
    """
    tempdir = Path(tempfile.mkdtemp())
    mp3s = [
        tempdir / 'first.mp3',
        tempdir / 'second.mp3',
        tempdir / 'third.mp3',
    ]
    new_args = [__file__]
    for mp3 in mp3s:
        shutil.copyfile(mp3file, mp3)
        new_args.append(str(mp3))

    monkeypatch.setattr(sys, 'argv', new_args)
    songs = parse_argv()
    songs = set(Path(s.filename) for s in songs)
    try:
        assert set(mp3s) == songs
    finally:
        shutil.rmtree(tempdir)


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
