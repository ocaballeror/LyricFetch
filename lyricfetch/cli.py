"""
Main module for CLI interaction.
"""
import sys
import os
import logging
import argparse
import glob

from . import logger
from . import CONFIG
from .song import Song
from .song import get_current_song
from .run import run


def load_from_file(filename):
    """
    Load a list of filenames from an external text file.
    """
    if os.path.isdir(filename):
        logger.error("Err: File '%s' is a directory", filename)
        return None
    if not os.path.isfile(filename):
        logger.error("Err: File '%s' does not exist", filename)
        return None

    try:
        with open(filename, 'r') as sourcefile:
            songs = [line.strip() for line in sourcefile]
    except IOError as error:
        logger.exception(error)
        return None
    songs = set(Song.from_filename(song) for song in songs)
    return songs.difference({None})  # In case any were in the wrong format


def parse_argv():
    """
    Parse command line arguments. Settings will be stored in the global
    variables declared above.
    """
    parser = argparse.ArgumentParser(description='Find lyrics for a set of mp3'
                                     ' files and embed them as metadata')
    parser.add_argument('-j', '--jobs', help='Number of parallel processes',
                        type=int, metavar='N', default=1)
    parser.add_argument('-o', '--overwrite', help='Overwrite lyrics of songs'
                        ' that already have them', action='store_true')
    parser.add_argument('-s', '--stats', help='Print a series of statistics at'
                        ' the end of the execution', action='store_true')
    parser.add_argument('-v', '--verbose', help='Set verbosity level (pass it'
                        ' up to three times)', action='count')
    parser.add_argument('-d', '--debug', help='Enable debug output',
                        action='store_true')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-r', '--recursive', help='Recursively search for'
                       ' mp3 files', metavar='path', nargs='?', const='.')
    group.add_argument('--from-file', help='Read a list of files from a text'
                       ' file', type=str)
    parser.add_argument('songs', help='The files/songs to search lyrics for',
                        nargs='*')

    args = parser.parse_args()

    CONFIG['overwrite'] = args.overwrite
    CONFIG['print_stats'] = args.stats

    if args.verbose is None or args.verbose == 0:
        logger.setLevel(logging.CRITICAL)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    if args.jobs <= 0:
        msg = 'Argument -j/--jobs should have a value greater than zero'
        parser.error(msg)
    else:
        CONFIG['jobcount'] = args.jobs

    songs = set()
    if args.from_file:
        songs = load_from_file(args.from_file)
        if not songs:
            raise ValueError('No file names found in file')
    elif args.recursive:
        mp3files = glob.iglob(args.recursive + '/**/*.mp3', recursive=True)
        songs = set(Song.from_filename(f) for f in mp3files)
    elif args.songs:
        if os.path.exists(args.songs[0]):
            parser = Song.from_filename
        else:
            parser = Song.from_string
        songs.update(map(parser, args.songs))
    else:
        songs.add(get_current_song())

    # Just in case some song constructors failed, remove all the Nones
    return songs.difference({None})


def main():
    """
    Main function.
    """
    msg = ''
    try:
        songs = parse_argv()
        if not songs:
            msg = 'No songs specified'
    except ValueError as error:
        msg = str(error)
    if msg:
        logger.error('%s: Error: %s', sys.argv[0], msg)
        return 1

    logger.debug('Running with %s', songs)
    try:
        run(songs)
    except KeyboardInterrupt:
        print('Interrupted')
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
