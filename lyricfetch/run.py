"""
All the functions and classes needed to actually perform the lyrics search.
"""
import os
import time
import math
import asyncio

from urllib.error import URLError, HTTPError
from http.client import HTTPException
from multiprocessing import Pool

import eyed3

from . import CONFIG
from . import logger
from . import sources
from .scraping import id_source
from .stats import Stats


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
        if not section:
            newlist.remove(source)
        else:
            pos = newlist.index(source) + 1
            if pos == len(sources):
                return []
            newlist = sources[pos:]
    return newlist


async def scrape(source, song):
    start = time.time()
    loop = asyncio.get_event_loop()
    try:
        lyrics = await loop.run_in_executor(None, source, song)
    except (HTTPError, HTTPException, URLError, ConnectionError):
        lyrics = ''

    res = dict(runtime=time.time() - start,
               lyrics=lyrics,
               source=source)
    return res


async def get_lyrics_async(song, l_sources):
    """
    Asynchronously searches for the lyrics of the specified song using the list
    of sources provided.

    Returns a Result object with the song, the first source that returned valid
    lyrics and a runtimes dictionary with all the other scraping attempts.
    """
    runtimes = {}
    tasks = [asyncio.ensure_future(scrape(src, song)) for src in l_sources]

    for future in asyncio.as_completed(tasks):
        result = await future
        runtimes[result['source']] = result['runtime']
        if result['lyrics']:
            break

    for task in tasks:
        task.cancel()

    if result['lyrics']:
        song.lyrics = result['lyrics']
        source = result['source']
    else:
        source = None

    return Result(song, source, runtimes)


def get_lyrics(song, l_sources=None):
    """
    A wrapper around `get_lyrics_threaded` that takes care of setting up the
    asyncio loop and waiting for the function to return.
    """
    if l_sources is None:
        l_sources = sources

    if song.lyrics and not CONFIG['overwrite']:
        logger.debug('%s already has embedded lyrics', song)
        return None

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(get_lyrics_async(song, l_sources))
    return res


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
    Calls get_lyrics for a song or list of songs.
    """
    if not hasattr(songs, '__iter__'):
        result = get_lyrics(songs)
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
