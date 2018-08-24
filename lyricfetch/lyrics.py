#!/usr/bin/env python3

"""
Find lyrics for all the .mp3 files in the current directory
and write them as metadata for the files
"""
#
# LIST OF LYRICS SITES (X marks implemented)
# lyrics.wikia.com    X
# metrolyrics.com     X
# azlyrics.com        X
# lyrics.com          X
# darklyrics.com      X
# genius.com          X
# vagalume.com.br     X
# musixmatch.com      X
# songlyrics.com
# lyricsmode.com      X
# metal-archives.com  X
# letras.mus.br       X

import sys
import os
import time
import re
import math
import argparse
import importlib
import glob
import logging
import ssl
import json
import threading
from collections import defaultdict
from queue import Queue
from pathlib import Path

import urllib.request as request
from urllib.error import URLError, HTTPError
from http.client import HTTPException
from multiprocessing import Pool

import eyed3
from bs4 import BeautifulSoup

from . import CONFIG
from . import URLESCAPE
from . import URLESCAPES

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Send verbose logs to a log file
# debuglogger = logging.FileHandler('debuglog', 'w')
# debuglogger.setLevel(logging.DEBUG)
# logger.addHandler(debuglogger)

# Send error logs to an errlog file
# errlogger = logging.FileHandler('errlog', 'w')
# errlogger.setLevel(logging.WARNING)
# logger.addHandler(errlogger)

# Discard eyed3 messages unless they're important
logging.getLogger('eyed3.mp3.headers').setLevel(logging.CRITICAL)


def get_url(url, parser='html'):
    """
    Requests the specified url and returns a BeautifulSoup object with its
    contents.
    """
    url = request.quote(url, safe=':/?=&')
    logger.debug('URL: %s', url)
    req = request.Request(url, headers={'User-Agent': 'foobar'})
    try:
        response = request.urlopen(req)
    except HTTPError:
        raise
    except (ssl.SSLError, URLError):
        # Some websites (like metal-archives) use older TLS versions and can
        # make the ssl module trow a VERSION_TOO_LOW error. Here we try to use
        # the older TLSv1 to see if we can fix that
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        response = request.urlopen(req, context=context)

    response = response.read()
    if parser == 'html':
        return BeautifulSoup(response, 'html.parser')
    elif parser == 'json':
        return json.loads(response)
    elif parser == 'raw':
        return response.decode()
    raise ValueError('Unrecognized parser')


def get_lastfm(method, lastfm_key='', **kwargs):
    """
    Request the specified method from the lastfm api.
    """
    if not lastfm_key:
        if 'lastfm_key' not in CONFIG or not CONFIG['lastfm_key']:
            logger.warning('No lastfm key configured')
            return ''
        else:
            lastfm_key = CONFIG['lastfm_key']

    url = 'http://ws.audioscrobbler.com/2.0/?method={}&api_key={}&format=json'
    url = url.format(method, lastfm_key)
    for key in kwargs:
        url += '&{}={}'.format(key, kwargs[key])

    response = get_url(url, parser='json')
    if 'error' in response:
        logger.error('Error number %d in lastfm query: %s',
                     response['error'], response['message'])
        return ''

    return response


def normalize(string, chars_to_remove=None, replacement=''):
    """
    Remove accented characters and such.

    The argument chars_to_remove is a dictionary that maps a string of chars to
    a single character. Every occurrence of every character in the first string
    will be replaced by that second character passed as value. If only one
    mapping is desired, chars_to_remove may be a single string, but a third
    parameter, replacement, must be provided to complete the translation.
    """
    ret = string.translate(str.maketrans({
        'á': 'a',
        'ä': 'a',
        'æ': 'ae',
        'é': 'e',
        'í': 'i',
        'ó': 'o',
        'ö': 'o',
        'ú': 'u',
        'ü': 'u',
        'ñ': 'n',
    }))

    if isinstance(chars_to_remove, dict):
        for chars, replace in chars_to_remove.items():
            reg = '[' + re.escape(chars) + ']'
            ret = re.sub(reg, replace, ret)

    elif isinstance(chars_to_remove, str):
        reg = '[' + re.escape(chars_to_remove) + ']'
        ret = re.sub(reg, replacement, ret)

    return ret


def metrolyrics(song):
    """
    Returns the lyrics found in metrolyrics for the specified mp3 file or an
    empty string if not found.
    """
    translate = {URLESCAPE: '', ' ': '-'}
    title = song.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)

    url = 'http://www.metrolyrics.com/{}-lyrics-{}.html'.format(title, artist)
    soup = get_url(url)
    body = soup.find(id='lyrics-body-text')
    if body is None:
        return ''

    text = ''
    verses = body.find_all('p')
    for verse in verses:
        text += verse.get_text().strip()
        text += '\n\n'

    return text.strip()


def darklyrics(song):
    """
    Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found.
    """

    # Darklyrics relies on the album name
    if not hasattr(song, 'album') or not song.album:
        song.fetch_album_name()
        if not hasattr(song, 'album') or not song.album:
            # If we don't have the name of the album, there's nothing we can do
            # on darklyrics
            return ''

    artist = song.artist.lower()
    artist = normalize(artist, URLESCAPES, '')
    album = song.album.lower()
    album = normalize(album, URLESCAPES, '')
    title = song.title

    url = 'http://www.darklyrics.com/lyrics/{}/{}.html'.format(artist, album)
    soup = get_url(url)
    text = ''
    for header in soup.find_all('h3'):
        song = str(header.get_text())
        next_sibling = header.next_sibling
        if song.lower().find(title.lower()) != -1:
            while next_sibling is not None and\
                    (next_sibling.name is None or next_sibling.name != 'h3'):
                if next_sibling.name is None:
                    text += str(next_sibling)
                next_sibling = next_sibling.next_sibling

    return text.strip()


def azlyrics(song):
    """
    Returns the lyrics found in azlyrics for the specified mp3 file or an empty
    string if not found.
    """
    artist = song.artist.lower()
    if artist[0:2] == 'a ':
        artist = artist[2:]
    artist = normalize(artist, URLESCAPES, '')
    title = song.title.lower()
    title = normalize(title, URLESCAPES, '')

    url = 'https://www.azlyrics.com/lyrics/{}/{}.html'.format(artist, title)
    soup = get_url(url)
    body = soup.find_all('div', class_='')[-1]
    return body.get_text().strip()


def genius(song):
    """
    Returns the lyrics found in genius.com for the specified mp3 file or an
    empty string if not found.
    """
    translate = {
        '@': 'at',
        '&': 'and',
        URLESCAPE: '',
        ' ': '-'
    }
    artist = song.artist.capitalize()
    artist = normalize(artist, translate)
    title = song.title.capitalize()
    title = normalize(title, translate)

    url = 'https://www.genius.com/{}-{}-lyrics'.format(artist, title)
    soup = get_url(url)
    for content in soup.find_all('p'):
        if content:
            text = content.get_text().strip()
            if text:
                return text

    return ''


def metalarchives(song):
    """
    Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found.
    """
    artist = normalize(song.artist)
    title = normalize(song.title)

    url = 'https://www.metal-archives.com/search/ajax-advanced/searching/songs'
    url += f'/?songTitle={title}&bandName={artist}&ExactBandMatch=1'
    soup = get_url(url, parser='json')
    if not soup:
        return ''

    song_id_re = re.compile(r'lyricsLink_([0-9]*)')
    ids = set(re.search(song_id_re, a) for sub in soup['aaData'] for a in sub)
    if not ids:
        return ''

    if None in ids:
        ids.remove(None)
    ids = map(lambda a: a.group(1), ids)
    for song_id in ids:
        url = 'https://www.metal-archives.com/release/ajax-view-lyrics/id/{}'
        lyrics = get_url(url.format(song_id), parser='html')
        lyrics = lyrics.get_text().strip()
        if not re.search('lyrics not available', lyrics):
            return lyrics

    return ''


def lyricswikia(song):
    """
    Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or
    an empty string if not found.
    """
    artist = song.artist.title()
    artist = normalize(artist, ' ', '_')
    title = song.title
    title = normalize(title, ' ', '_')

    url = 'https://lyrics.wikia.com/wiki/{}:{}'.format(artist, title)
    soup = get_url(url)
    text = ''
    content = soup.find('div', class_='lyricbox')
    if not content:
        return ''

    for unformat in content.findChildren(['i', 'b']):
        unformat.unwrap()
    for remove in content.findChildren(['div', 'span']):
        remove.decompose()

    nlcount = 0
    for line in content.children:
        if line is None or line == '<br/>' or line == '\n':
            if nlcount == 2:
                text += '\n\n'
                nlcount = 0
            else:
                nlcount += 1
        else:
            nlcount = 0
            text += str(line).replace('<br/>', '\n')
    return text.strip()


def musixmatch(song):
    """
    Returns the lyrics found in musixmatch for the specified mp3 file or an
    empty string if not found.
    """
    escape = re.sub("'-¡¿", '', URLESCAPE)
    translate = {
        escape: '',
        ' ': '-'
    }
    artist = song.artist.title()
    artist = re.sub(r"( '|' )", '', artist)
    artist = re.sub(r"'", '-', artist)
    title = song.title
    title = re.sub(r"( '|' )", '', title)
    title = re.sub(r"'", '-', title)

    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url = 'https://www.musixmatch.com/lyrics/{}/{}'.format(artist, title)
    soup = get_url(url)
    text = ''
    contents = soup.find_all('p', class_='mxm-lyrics__content ')
    for p in contents:
        text += p.get_text().strip()
        if p != contents[-1]:
            text += '\n\n'

    return text.strip()


# Songlyrics is basically a mirror for musixmatch, so it helps us getting
# around musixmatch's bot detection (they block IPs pretty easily)
def songlyrics(song):
    """
    Returns the lyrics found in songlyrics.com for the specified mp3 file or an
    empty string if not found.
    """
    translate = {
        URLESCAPE: '',
        ' ': '-'
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    artist = re.sub(r'\-{2,}', '-', artist)
    title = re.sub(r'\-{2,}', '-', title)

    url = 'http://www.songlyrics.com/{}/{}-lyrics'.format(artist, title)
    soup = get_url(url)
    text = soup.find(id='songLyricsDiv')
    if not text:
        return ''

    text = text.getText().strip()
    if not text or text.lower().startswith('we do not have the lyrics for'):
        return ''

    return text


def lyricscom(song):
    """
    Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found.
    """
    artist = song.artist.lower()
    artist = normalize(artist, ' ', '+')
    title = song.title

    url = 'https://www.lyrics.com/artist/{}'.format(artist)
    soup = get_url(url)
    location = ''
    for a in soup.select('tr a'):
        if a.string.lower() == title.lower():
            location = a['href']
            break
    if location == '':
        return ''

    url = 'https://www.lyrics.com' + location
    soup = get_url(url)
    body = soup.find(id='lyric-body-text')
    if not body:
        return ''

    return body.get_text().strip()


def vagalume(song):
    """
    Returns the lyrics found in vagalume.com.br for the specified mp3 file or
    an empty string if not found.
    """
    translate = {
        '@': 'a',
        URLESCAPE: '',
        ' ': '-'
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = song.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url = 'https://www.vagalume.com.br/{}/{}.html'.format(artist, title)
    soup = get_url(url)
    body = soup.select('div#lyrics')
    if body == []:
        return ''

    content = body[0]
    for br in content.find_all('br'):
        br.replace_with('\n')

    return content.get_text().strip()


def lyricsmode(song):
    """
    Returns the lyrics found in lyricsmode.com for the specified mp3 file or an
    empty string if not found.
    """
    translate = {
        URLESCAPE: '',
        ' ': '_'
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    artist = re.sub(r'\_{2,}', '_', artist)
    title = re.sub(r'\_{2,}', '_', title)

    if artist[0:4].lower() == 'the ':
        artist = artist[4:]

    if artist[0:2].lower() == 'a ':
        prefix = artist[2]
    else:
        prefix = artist[0]

    url = 'http://www.lyricsmode.com/lyrics/{}/{}/{}.html'
    url = url.format(prefix, artist, title)
    soup = get_url(url)
    content = soup.find(id='lyrics_text')

    return content.get_text().strip()


def letras(song):
    """
    Returns the lyrics found in letras.com for the specified mp3 file or an
    empty string if not found.
    """
    translate = {
        '&': 'a',
        URLESCAPE: '',
        ' ': '-'
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    url = 'https://www.letras.com/{}/{}/'.format(artist, title)
    soup = get_url(url)
    if not soup:
        return ''

    found_title = soup.select_one('div.cnt-head_title h1')
    if not found_title:
        # The site didn't find lyrics and took us to the homepage
        return ''

    found_title = found_title.get_text()
    found_title = re.sub(r'[\W_]+', '', found_title.lower())
    if found_title != re.sub(r'[\W_]+', '', song.title.lower()):
        # The site took us to the wrong song page
        return ''

    content = soup.find('article')
    if not content:
        return ''

    text = ''
    for br in content.find_all('br'):
        br.replace_with('\n')

    for p in content.find_all('p'):
        text += p.get_text() + '\n\n'

    return text.strip()


sources = [
    azlyrics,
    metrolyrics,
    lyricswikia,
    darklyrics,
    metalarchives,
    genius,
    musixmatch,
    songlyrics,
    vagalume,
    letras,
    lyricsmode,
    lyricscom
]

source_ids = {
    azlyrics: ('AZL', 'AZLyrics.com'),
    metrolyrics: ('MET', 'Metrolyrics.com'),
    lyricswikia: ('WIK', 'Lyrics.wikia.com'),
    darklyrics: ('DAR', 'Darklyrics.com'),
    metalarchives: ('ARC', 'Metal-archives.com'),
    genius: ('GEN', 'Genius.com'),
    musixmatch: ('XMA', 'Musixmatch.com'),
    songlyrics: ('SON', 'SongLyrics.com'),
    vagalume: ('VAG', 'Vagalume.com.br'),
    letras: ('LET', 'Letras.com'),
    lyricsmode: ('LYM', 'Lyricsmode.com'),
    lyricscom: ('LYC', 'Lyrics.com'),
}


def id_source(source, full=False):
    """
    Returns the name of a website-scrapping function.
    """
    if source not in source_ids:
        return ''

    if full:
        return source_ids[source][1]
    else:
        return source_ids[source][0]


def avg(values):
    """
    Returns the average of a sequence of numbers.
    """
    if not values:
        return 0
    else:
        return sum(values) / len(values)


class Record:
    """
    Defines an entry in the stats 'database'. Packs a set of information about
    an execution of the scrapping functions. This class is auxiliary to Stats.
    """
    def __init__(self):
        self.successes = 0
        self.fails = 0
        self.runtimes = []

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"""Successes: {self.successes}
Fails: {self.fails}
Success rate: {self.success_rate():.2f}%
Average runtime: {avg(self.runtimes):.2f}s"""

    def add_runtime(self, runtime):
        """
        Add a new runtime to the runtimes dictionary.
        """
        if runtime != 0:
            self.runtimes.append(runtime)

    def success_rate(self):
        """
        Returns a float with the rate of success from all the logged results.
        """
        if self.successes + self.fails == 0:
            success_rate = 0
        else:
            total_attempts = self.successes + self.fails
            success_rate = (self.successes * 100 / total_attempts)

        return success_rate


class Stats:
    """
    Stores a series of statistics about the execution of the program.
    """
    def __init__(self):
        # Maps every lyrics scraping function to a Record object
        self.source_stats = defaultdict(Record)

    def add_result(self, source, found, runtime):
        """
        Adds a new record to the statistics 'database'. This function is
        intended to be called after a website has been scraped. The arguments
        indicate the function that was called, the time taken to scrap the
        website and a boolean indicating if the lyrics were found or not.
        """
        self.source_stats[source.__name__].add_runtime(runtime)
        if found:
            self.source_stats[source.__name__].successes += 1
        else:
            self.source_stats[source.__name__].fails += 1

    def avg_time(self, source=None):
        """
        Returns the average time taken to scrape lyrics. If a string or a
        function is passed as source, return the average time taken to scrape
        lyrics from that source, otherwise return the total average.
        """
        if source is None:
            runtimes = []
            for rec in self.source_stats.values():
                runtimes.extend([r for r in rec.runtimes if r != 0])
            return avg(runtimes)
        else:
            if callable(source):
                return avg(self.source_stats[source.__name__].runtimes)
            else:
                return avg(self.source_stats[source].runtimes)

    def calculate(self):
        """
        Calculate the overall counts of best, worst, fastest, slowest, total
        found, total not found and total runtime

        Results are returned in a dictionary with the above parameters as keys.
        """
        best, worst, fastest, slowest = (), (), (), ()
        found = notfound = total_time = 0
        for source, rec in self.source_stats.items():
            if not best or rec.successes > best[1]:
                best = (source, rec.successes, rec.success_rate())
            if not worst or rec.successes < worst[1]:
                worst = (source, rec.successes, rec.success_rate())

            avg_time = self.avg_time(source)
            if not fastest or (avg_time != 0 and avg_time < fastest[1]):
                fastest = (source, avg_time)
            if not slowest or (avg_time != 0 and avg_time > slowest[1]):
                slowest = (source, avg_time)

            found += rec.successes
            notfound += rec.fails
            total_time += sum(rec.runtimes)

        return {
            'best': best,
            'worst': worst,
            'fastest': fastest,
            'slowest': slowest,
            'found': found,
            'notfound': notfound,
            'total_time': total_time
        }

    def print_stats(self):
        """
        Print a series of relevant stats about a full execution. This function
        is meant to be called at the end of the program.
        """
        stats = self.calculate()
        total_time = '%d:%02d:%02d' % (stats['total_time'] / 3600,
                                       (stats['total_time'] / 3600) / 60,
                                       (stats['total_time'] % 3600) % 60)
        output = """\
Total runtime: {total_time}
    Lyrics found: {found}
    Lyrics not found:{notfound}
    Most useful source:\
{best} ({best_count} lyrics found) ({best_rate:.2f}% success rate)
    Least useful source:\
{worst} ({worst_count} lyrics found) ({worst_rate:.2f}% success rate)
    Fastest website to scrape: {fastest} (Avg: {fastest_time:.2f}s per search)
    Slowest website to scrape: {slowest} (Avg: {slowest_time:.2f}s per search)
    Average time per website: {avg_time:.2f}s

xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxx    PER WEBSITE STATS:      xxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""
        output = output.format(total_time=total_time,
                               found=stats['found'],
                               notfound=stats['notfound'],
                               best=stats['best'][0].capitalize(),
                               best_count=stats['best'][1],
                               best_rate=stats['best'][2],
                               worst=stats['worst'][0].capitalize(),
                               worst_count=stats['worst'][1],
                               worst_rate=stats['worst'][2],
                               fastest=stats['fastest'][0].capitalize(),
                               fastest_time=stats['fastest'][1],
                               slowest=stats['slowest'][0].capitalize(),
                               slowest_time=stats['slowest'][1],
                               avg_time=self.avg_time())
        for source in sources:
            stat = str(self.source_stats[source.__name__])
            output += f'\n{source.__name__.upper()}\n{stat}\n'

        print(output)


class Song:
    """
    Representation of a song object.

    It contains the basic metadata (artist, title) and optionally the lyrics,
    album and filepath to the corresponding mp3 if applicable.

    Instead of the typical constructor, one of the 3 classmethods should be use
    to create a song object. Either from_filename, from_info or from_string
    depending on the use case.
    """
    def __init__(self):
        self.artist = ''
        self.title = ''
        self.album = ''
        self.lyrics = ''

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.artist and self.title and not hasattr(self, 'filename'):
            return f'{self.artist.title()} - {self.title.title()}'
        elif self.filename:
            return self.filename
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
        song = cls.__new__(cls)
        song.__init__()

        song.filename = filename
        song.title = tags.title
        song.album = tags.album
        song.lyrics = ''.join([l.text for l in tags.lyrics])
        song.artist = tags.album_artist
        if not song.artist:
            song.artist = tags.artist

        return song

    @classmethod
    def from_info(cls, artist, title, album=''):
        """
        Class constructor to create a Song object by directly specifying the
        metadata.
        """
        song = cls.__new__(cls)
        song.__init__()

        if not artist or not title:
            logger.error('Incomplete song info')
            return None

        song.artist = artist
        song.title = title
        song.album = album

        return song

    @classmethod
    def from_string(cls, name, separator='-', reverse=False):
        """
        Class constructor using a string with the artist and title. This should
        be used when parsing user input, since all the information must be
        specified in a single string formatted as: '{artist} - {title}'.
        """
        song = cls.__new__(cls)
        song.__init__()

        recv = [t.strip() for t in name.split(separator)]
        if len(recv) < 2:
            logger.error('Wrong format!')
            return None

        if reverse:
            song.title = recv[0]
            song.artist = ''.join(recv[1:])
        else:
            song.artist = recv[0]
            song.title = ''.join(recv[1:])

        if not song.artist or not song.title:
            logger.error('Wrong format!')
            return None

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
            except Exception as error:
                print(error)
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
    this_module = importlib.import_module(__name__)
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
                       ' mp3 files', nargs='?', const='.')
    group.add_argument('-n', '--by-name', help='A list of song names in'
                       " 'artist - title' format", nargs='*')
    group.add_argument('--from-file', help='Read a list of files from a text'
                       ' file', type=str)
    parser.add_argument('files', help='The mp3 files to search lyrics for',
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

    if args.jobs is not None:
        if args.jobs <= 0:
            error = 'Argument -j/--jobs should have a value greater than zero'
            raise ValueError(error)
        else:
            CONFIG['jobcount'] = args.jobs

    songs = set()
    if args.by_name:
        for song in args.by_name:
            songs.add(Song.from_string(song))
    elif args.from_file:
        songs = load_from_file(args.from_file)
        if not songs:
            raise ValueError('No file names found in file')
    else:
        mp3files = []
        if args.files:
            mp3files = args.files
        elif args.recursive:
            mp3files = glob.iglob(args.recursive + '/**/*.mp3', recursive=True)
        else:
            raise ValueError('No files specified')

        songs = set(Song.from_filename(f) for f in mp3files)

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
