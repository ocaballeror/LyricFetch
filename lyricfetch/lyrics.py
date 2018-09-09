"""
Song representation and functions to actually get lyrics.
"""
import os
import time
import math
import importlib
import threading
from queue import Queue
from pathlib import Path

from urllib.error import URLError, HTTPError
from http.client import HTTPException
from multiprocessing import Pool

import eyed3

from . import CONFIG
from . import logger
from . import sources
from .scraping import id_source
from .scraping import get_lastfm
from .stats import Stats


class Song:
    """
    Representation of a song object.

    It contains the basic metadata (artist, title) and optionally the lyrics,
    album and filepath to the corresponding mp3 if applicable.

    Instead of the typical constructor, one of the 3 classmethods should be use
    to create a song object. Either from_filename, from_info or from_string
    depending on the use case.
    """
    def __init__(self, artist='', title='', album='', lyrics=''):
        self.artist = artist
        self.title = title
        self.album = album
        self.lyrics = lyrics

    def __repr__(self):
        items = self.__dict__.copy()
        del items['lyrics']
        values = ('='.join((k, v)) for k, v in items.items() if v)
        return 'Song({})'.format(', '.join(values))

    def __str__(self):
        if hasattr(self, 'filename'):
            return self.filename
        elif self.artist and self.title:
            return f'{self.artist.title()} - {self.title.title()}'
        else:
            return ''

    def __eq__(self, other):
        if hasattr(self, 'filename') and hasattr(other, 'filename'):
            return Path(self.filename) == Path(other.filename)
        else:
            equal = self.artist.lower() == other.artist.lower()
            equal = equal and self.title.lower() == other.title.lower()
            return equal

    def __hash__(self):
        if hasattr(self, 'filename'):
            return hash(self.filename)
        return hash((self.artist, self.title, self.album))

    @classmethod
    def from_filename(cls, filename):
        """
        Class constructor using the path to the corresponding mp3 file. The
        metadata will be read from this file to create the song object, so it
        must at least contain valid ID3 tags for artist and title.
        """
        if not filename:
            logger.error('No filename specified')
            return None

        if not os.path.exists(filename):
            logger.error("Err: File '%s' does not exist", filename)
            return None

        if os.path.isdir(filename):
            logger.error("Err: File '%s' is a directory", filename)
            return None

        try:
            audiofile = eyed3.load(filename)
        except Exception as error:
            print(type(error), error)
            return None

        # Sometimes eyed3 may return a null object and not raise any exceptions
        if audiofile is None:
            return None

        tags = audiofile.tag
        album = tags.album
        title = tags.title
        lyrics = ''.join([l.text for l in tags.lyrics])
        artist = tags.album_artist
        if not artist:
            artist = tags.artist

        song = cls(artist, title, album, lyrics)
        song.filename = filename
        return song

    @classmethod
    def from_string(cls, name, separator='-', reverse=False):
        """
        Class constructor using a string with the artist and title. This should
        be used when parsing user input, since all the information must be
        specified in a single string formatted as: '{artist} - {title}'.
        """
        recv = [t.strip() for t in name.split(separator)]
        if len(recv) < 2:
            logger.error('Wrong format!')
            return None

        if reverse:
            title = recv[0]
            artist = ''.join(recv[1:])
        else:
            artist = recv[0]
            title = ''.join(recv[1:])

        if not artist or not title:
            logger.error('Wrong format!')
            return None

        song = cls(artist, title)
        return song

    def fetch_album_name(self):
        """
        Get the name of the album from lastfm.
        """
        response = get_lastfm('track.getInfo', artist=self.artist,
                              track=self.title)
        if response:
            try:
                self.album = response['track']['album']['title']
                logger.debug('Found album %s from lastfm', self.album)
            except Exception:
                logger.warning('Could not fetch album name for %s', self)
        else:
            logger.warning('Could not fetch album name for %s', self)


class LyrThread(threading.Thread):
    """
    Threaded object to search for lyrics.
    """
    def __init__(self, source, song, queue):
        super().__init__()
        self.source = source
        self.song = song
        self.queue = queue

    def run(self):
        start = time.time()
        try:
            lyrics = self.source(self.song)
        except (HTTPError, HTTPException, URLError, ConnectionError):
            lyrics = ''

        res = dict(runtime=time.time() - start,
                   lyrics=lyrics,
                   source=self.source)
        self.queue.put(res)


class Result:
    """
    Contains the results generated from run, so they can be returned as a
    single variable.
    """
    def __init__(self, song, source=None, runtimes=None):
        self.song = song

        # The source where the lyrics were found (or None if they weren't)
        self.source = source

        # A dictionary that maps every source to the time taken to scrape
        # the website. Keys corresponding to unused sources will be missing
        if runtimes is None:
            self.runtimes = {}
        else:
            self.runtimes = runtimes


def exclude_sources(exclude, section=False):
    """
    Returns a narrower list of sources.

    If the exclude parameter is a list, every one of its items will be removed
    from the returned list.
    If it's just a function (or a function's name) and 'section' is set to
    False (default), a copy of the sources list without this element will be
    returned.
    If it's a function (or a function's name) but the section parameter is set
    to True, the returned list will be a section of the sources list, including
    everything between 'exclude' and the end of the list.
    """
    newlist = sources.copy()
    if not isinstance(exclude, list):
        exclude = [exclude]

    for source in exclude:
        if callable(source):
            newlist = _exclude_callable(source, newlist, section)
        if isinstance(source, str):
            newlist = _exclude_string(source, newlist, section)
    return newlist


def _exclude_callable(func, s_list, section):
    """
    Exclude a function from a list of sources.
    """
    if not section:
        s_list.remove(func)
    else:
        pos = s_list.index(func)
        s_list = sources[pos:]
    return s_list


def _exclude_string(name, s_list, section):
    """
    Exclude a function (specified by name) from a list of sources.
    """
    this_module = importlib.import_module(__name__.split('.')[0])
    if hasattr(this_module, name):
        func = getattr(this_module, name)
        logger.debug('Using new source %s', func.__name__)
        s_list = _exclude_callable(func, s_list, section)

    return s_list


def get_lyrics(song, l_sources=None):
    """
    Searches for lyrics of a single song and returns a Result object with the
    various stats collected in the process.

    The optional parameter 'sources' specifies an alternative list of sources.
    If not present, the main list will be used.
    """
    if l_sources is None:
        l_sources = sources

    if song.lyrics and not CONFIG['overwrite']:
        logger.debug('%s already has embedded lyrics', song)
        return None

    runtimes = {}
    source = None
    for l_source in l_sources:
        start = time.time()
        try:
            lyrics = l_source(song)
        except (HTTPError, HTTPException, URLError, ConnectionError):
            lyrics = ''

        runtimes[l_source] = time.time() - start
        if lyrics != '':
            source = l_source
            break

    if lyrics != '':
        logger.info('++ %s: Found lyrics for %s\n', source.__name__, song)
        song.lyrics = lyrics
    else:
        logger.info("Couldn't find lyrics for %s\n", song)
        source = None

    return Result(song, source, runtimes)


def get_lyrics_threaded(song, l_sources=None):
    """
    Launches a pool of threads to search for the lyrics of a single song.

    The optional parameter 'sources' specifies an alternative list of sources.
    If not present, the main list will be used.
    """
    if l_sources is None:
        l_sources = sources

    if song.lyrics and not CONFIG['overwrite']:
        logger.debug('%s already has embedded lyrics', song)
        return None

    runtimes = {}
    queue = Queue()
    pool = [LyrThread(source, song, queue) for source in l_sources]
    for thread in pool:
        thread.start()

    for _ in range(len(pool)):
        result = queue.get()
        runtimes[result['source']] = result['runtime']
        if result['lyrics']:
            break

    if result['lyrics']:
        song.lyrics = result['lyrics']
        source = result['source']
    else:
        source = None

    return Result(song, source, runtimes)


def process_result(result):
    """
    Process a result object by:
        1. Saving the lyrics to the corresponding file(if applicable).
        2. Printing the lyrics or the corresponding error/success message.
        3. Returning a boolean indicating if the lyrics were found or not.
    """
    found = result.source is not None
    if found:
        if hasattr(result.song, 'filename'):
            audiofile = eyed3.load(result.song.filename)
            audiofile.tag.lyrics.set(result.song.lyrics)
            audiofile.tag.save()
            print(f'{id_source(result.source)} Lyrics added for {result.song}')
        else:
            print(f"""FROM {id_source(result.source, full=True)}

{result.song.lyrics}
-----------------------------------------------------------------------------\
""")
    else:
        print(f'Lyrics for {result.song} not found')

    return found


def run(songs):
    """
    Calls get_lyrics_threaded for a song or list of songs.
    """
    if not hasattr(songs, '__iter__'):
        result = get_lyrics_threaded(songs)
        process_result(result)
    else:
        start = time.time()
        stats = run_mp(songs)
        end = time.time()
        if CONFIG['print_stats']:
            stats.print_stats()
        total_time = end - start
        total_time = '%d:%02d:%02d' % (total_time / 3600,
                                       (total_time / 3600) / 60,
                                       (total_time % 3600) % 60)
        print(f'Total time: {total_time}')


def run_mp(songs):
    """
    Concurrently calls get_lyrics to fetch the lyrics of a large list of songs.
    """
    stats = Stats()
    if CONFIG['debug']:
        good = open('found', 'w')
        bad = open('notfound', 'w')

    logger.debug('Launching a pool of %d processes\n', CONFIG['jobcount'])
    chunksize = math.ceil(len(songs) / os.cpu_count())
    try:
        with Pool(CONFIG['jobcount']) as pool:
            for result in pool.imap_unordered(get_lyrics, songs, chunksize):
                if result is None:
                    continue

                for source, runtime in result.runtimes.items():
                    stats.add_result(source, result.source == source, runtime)

                found = process_result(result)
                if CONFIG['debug']:
                    if found:
                        good.write(f'{id_source(source)}: {result.song}\n')
                        good.flush()
                    else:
                        bad.write(str(result.song) + '\n')
                        bad.flush()

    finally:
        if CONFIG['debug']:
            good.close()
            bad.close()

    return stats
