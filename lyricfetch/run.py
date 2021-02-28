"""
All the functions and classes needed to actually perform the lyrics search.
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import List

from . import CONFIG
from . import logger
from . import sources
from .song import Song


@dataclass
class Result:
    """
    Contains the results generated from run, so they can be returned as a
    single variable.
    """
    song: Song

    # The source where the lyrics were found (or None if they weren't)
    source: str = None

    # A dictionary that maps every source to the time taken to scrape
    # the website. Keys corresponding to unused sources will be missing
    runtimes: dict = field(default_factory=dict)


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


async def scraper_wrapper(scraper, *args, **kwargs):
    """
    Auxiliary function that invokes a scraper and returns both the scraper
    function and the result of the call. This is useful for an
    `asyncio.as_completed` loop, where we may want to know which function has
    finished.
    """
    res = await scraper(*args, **kwargs)
    return (scraper, res)


async def get_song_lyrics(song: Song, l_sources: list = None) -> Result:
    """
    Searches for lyrics of a single song and returns a Result object with the
    song and the site where its lyrics were found (if any).

    The optional parameter 'sources' specifies an alternative list of sources.
    If not present, the main list will be used.
    """
    if l_sources is None:
        l_sources = sources

    if song.lyrics and not CONFIG['overwrite']:
        logger.debug('%s already has embedded lyrics', song)
        return None

    elapsed = 0
    start = time.time()
    tasks = (scraper_wrapper(func, song) for func in l_sources)
    futures = [asyncio.ensure_future(task) for task in tasks]
    for future in asyncio.as_completed(futures):
        try:
            source, lyrics = await future
        except Exception as e:
            logger.exception(e)
            lyrics = None

        if lyrics:
            elapsed = time.time() - start
            break

    for future in futures:
        future.cancel()

    if lyrics:
        logger.info('++ %s: Found lyrics for %s\n', source.__name__, song)
        song.lyrics = lyrics
    else:
        logger.info("Couldn't find lyrics for %s\n", song)
        source = None

    return Result(song, source, elapsed)


async def get_lyrics(songs: List[Song]):
    """
    Get lyrics for a song or list of songs.
    """
    if not hasattr(songs, '__iter__'):
        songs = [songs]

    for res in asyncio.as_completed([get_song_lyrics(song) for song in songs]):
        yield await res
