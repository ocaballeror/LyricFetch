"""
Module to test the different CLI arguments that can be passed.
"""
import random
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from py.path import local as pypath
from conftest import chdir
from conftest import tag_mp3

import lyricfetch
import lyricfetch.song
from lyricfetch import Song
from lyricfetch import CONFIG
from lyricfetch.cli import load_from_file
from lyricfetch.cli import main
from lyricfetch.cli import parse_argv


@pytest.mark.parametrize('arg,config', [
    ('-o', 'overwrite'),
    ('--overwrite', 'overwrite'),
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


def test_argv_empty(monkeypatch):
    """
    Check that, with no arguments, the program searches for the currently
    playing song.
    """
    current_song = Song('Fallujah', 'Assemblage of wolves')

    def fake_get_current_song():
        return current_song

    new_args = [__file__]
    monkeypatch.setattr(sys, 'argv', new_args)
    monkeypatch.setattr(lyricfetch.cli, 'get_current_song',
                        fake_get_current_song)
    songs = parse_argv()
    assert songs == set([current_song])


def test_argv_by_name(monkeypatch):
    """
    Check that the program accepts a song or list of songs by name, and
    returns a list of song objects with the information it parsed.
    """
    # Run it first with only one song
    artist, title = 'judas priest', 'no surrender'
    new_args = [__file__, f'{artist} - {title}']
    param_song = Song(artist, title)
    monkeypatch.setattr(sys, 'argv', new_args)
    songs = parse_argv()
    assert songs == set([param_song])

    # Then try with multiple songs
    param_songs = [
        Song('kreator', 'mars mantra'),
        Song('nervosa', 'morbid courage'),
        Song('ac/dc', 'night prowler'),
    ]
    new_args = [__file__]
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
        songs.append(Song(artist=artist, title=title))

    filelist = tmpdir / 'filelist'
    with open(filelist, 'w') as file:
        for filename in mp3_files:
            file.write(str(filename) + '\n')
        file.flush()

    monkeypatch.setattr(sys, 'argv', [__file__, '--from-file', str(filelist)])
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
    ['-r', '--from-file'],
    ['-n', '--from-file'],
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


def test_load_from_file_errors(tmpdir):
    """
    Test the errors that can be raised from `load_from_file()`.
    """
    assert load_from_file(tmpdir) is None

    tmpdir.remove()
    assert load_from_file(tmpdir) is None

    tmpdir.ensure(file=True)
    assert not load_from_file(tmpdir)


def test_main_errors(monkeypatch):
    """
    Test the different error conditions that can occur when calling `main()`.
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
    monkeypatch.setattr(lyricfetch.cli, 'parse_argv', empty_set)
    assert main() == 1

    # Make parse_argv() raise a ValueError
    monkeypatch.setattr(lyricfetch.cli, 'parse_argv', value_error)
    assert main() == 1

    # Interrupt the process with a keyboard interrupt
    monkeypatch.setattr(lyricfetch.cli, 'parse_argv', filled_set)
    monkeypatch.setattr(lyricfetch.cli, 'run', fake_run)
    assert main() == 1
