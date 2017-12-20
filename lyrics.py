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
# musica.com          X

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
import urllib.request as request

from urllib.error import URLError,HTTPError
from http.client import HTTPException
from multiprocessing import Pool
from bs4 import BeautifulSoup

import eyed3

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
logging.getLogger("eyed3.mp3.headers").setLevel(logging.CRITICAL)

def get_soup(url, safe=":/"):
    '''Requests the specified url and returns a BeautifulSoup object with its
    contents'''
    url = request.quote(url, safe=safe)
    logger.debug('URL: %s', url)
    req = request.Request(url, headers={"User-Agent": "foobar"})
    try:
        response = request.urlopen(req)
    except (ssl.SSLError, URLError):
        # Some websites (like metal-archives) use older TLS versions and can
        # make the ssl module trow a VERSION_TOO_LOW error. Here we try to use
        # the older TLSv1 to see if we can fix that
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        response = request.urlopen(req, context=context)

    return BeautifulSoup(response.read(), 'html.parser')

# Contains the characters usually removed or replaced in URLS
URLESCAPE = ".¿?%_@,;&\\/()'\"-!¡"
URLESCAPES = URLESCAPE + ' '

def normalize(string, chars_to_remove=None, replacement=''):
    """Remove accented characters and such.
    The argument charsToRemove is a dictionary that maps a string of chars
    to a single character. Every ocurrence of every character in the first
    string will be replaced by that second charcter passed as value. If only
    one mapping is desired, charsToRemove may be a single string, but a third
    parameter, replacement, must be provided to complete the translation."""

    ret = string.translate(str.maketrans({
        'á': 'a',
        'é': 'e',
        'í': 'i',
        'ó': 'o',
        'ö': 'o',
        'ú': 'u',
        'ü': 'u',
        'ñ': 'n'
    }))

    if isinstance(chars_to_remove, dict):
        for chars, replace in chars_to_remove.items():
            reg = "["+re.escape(chars)+"]"
            ret = re.sub(reg, replace, ret)

    elif isinstance(chars_to_remove, str):
        reg = '['+re.escape(chars_to_remove)+']'
        ret = re.sub(reg, replacement, ret)

    return ret

def metrolyrics(song):
    '''Returns the lyrics found in metrolyrics for the specified mp3 file or an
    empty string if not found'''
    translate = {URLESCAPE: "", " ":"-"}
    title = song.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)

    url = "http://www.metrolyrics.com/{}-lyrics-{}.html".format(title, artist)
    soup = get_soup(url)
    body = soup.find(id="lyrics-body-text")
    if body is None:
        return ""

    text = ""
    verses = body.find_all('p')
    for verse in verses:
        text += verse.get_text().strip()
        text += '\n\n'

    return text.strip()

def darklyrics(song):
    '''Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found'''
    if not hasattr(song, 'album') or not song.album:
        # DarkLyrics can't be used without the album name for now
        return ''

    artist = song.artist.lower()
    artist = normalize(artist, URLESCAPES, '')
    album = song.album.lower()
    album = normalize(album, URLESCAPES, '')
    title = song.title

    url = "http://www.darklyrics.com/lyrics/{}/{}.html".format(artist, album)
    soup = get_soup(url)
    text = ""
    for header in soup.find_all('h3'):
        song = str(header.get_text())
        next_sibling = header.next_sibling
        if song.lower().find(title.lower()) != -1:
            while next_sibling is not None and (next_sibling.name is None\
                or next_sibling.name != 'h3'):
                if next_sibling.name is None:
                    text += str(next_sibling)
                next_sibling = next_sibling.next_sibling

    return text.strip()

def azlyrics(song):
    '''Returns the lyrics found in azlyrics for the specified mp3 file or an
    empty string if not found'''
    artist = song.artist.lower()
    if artist[0:2] == "a ":
        artist = artist[2:]
    artist = normalize(artist, URLESCAPES, "")
    title = song.title.lower()
    title = normalize(title, URLESCAPES, "")

    url = "https://www.azlyrics.com/lyrics/{}/{}.html".format(artist, title)
    soup = get_soup(url)
    body = soup.find_all('div', class_="")[-1]
    return body.get_text().strip()

def genius(song):
    '''Returns the lyrics found in genius.com for the specified mp3 file or an
    empty string if not found'''
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

    url = "https://www.genius.com/{}-{}-lyrics".format(artist, title)
    soup = get_soup(url)
    for content in soup.find_all('p'):
        if content:
            text = content.get_text().strip()
            if text:
                return text

    return ''

def metalarchives(song):
    '''Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found'''
    artist = song.artist.capitalize()
    artist = normalize(artist, ' ', '_')
    title = song.title.capitalize()
    title = normalize(title, ' ', '_')

    url = "https://www.metal-archives.com/search/ajax-advanced/searching/songs/"
    url += f"?songTitle={title}&bandName={artist}&exactBandMatch=1"
    soup = get_soup(url, safe=':/?=&')

    song_id = ''
    song_id_re = re.compile(r'lyricsLink_([0-9]*)')
    for link in soup.find_all('a'):
        song_id = re.search(song_id_re, str(link))
        if song_id:
            song_id = song_id.group(1)
            break

    if not song_id:
        return ""

    url = "https://www.metal-archives.com/release/ajax-view-lyrics/id/{}".format(song_id)
    soup = get_soup(url)
    text = soup.get_text()
    if re.search('lyrics not available', text):
        return ""
    else:
        return text.strip()

def lyricswikia(song):
    '''Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or an
    empty string if not found'''
    artist = song.artist.title()
    artist = normalize(artist, ' ', '_')
    title = song.title
    title = normalize(title, ' ', '_')

    url = "https://lyrics.wikia.com/wiki/{}:{}".format(artist, title)
    soup = get_soup(url)
    text = ""
    content = soup.find('div', class_='lyricbox')
    if not content:
        return ""

    for unformat in content.findChildren(['i', 'b']):
        unformat.unwrap()
    for remove in content.findChildren('div'):
        remove.decompose()

    nlcount = 0
    for line in content.children:
        if line is None or line == '<br/>' or line == '\n':
            if nlcount == 2:
                text += "\n\n"
                nlcount = 0
            else:
                nlcount += 1
        else:
            nlcount = 0
            text += str(line).replace('<br/>', '\n')
    return text.strip()

def musixmatch(song):
    '''Returns the lyrics found in musixmatch for the specified mp3 file or an
    empty string if not found'''
    escape = re.sub("'-¡¿", '', URLESCAPE)
    translate = {
        escape: "",
        " ": "-"
    }
    artist = song.artist.title()
    artist = re.sub(r"( '|' )", "", artist)
    artist = re.sub(r"'", "-", artist)
    title = song.title
    title = re.sub(r"( '|' )", "", title)
    title = re.sub(r"'", "-", title)

    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url = "https://www.musixmatch.com/lyrics/{}/{}".format(artist, title)
    soup = get_soup(url)
    text = ""
    contents = soup.find_all('p', class_='mxm-lyrics__content ')
    for p in contents:
        text += p.get_text().strip()
        if p != contents[-1]:
            text += '\n\n'

    return text.strip()

# Songlyrics is basically a mirror for musixmatch, so it helps us getting
# around musixmatch's bot detection (they block IPs pretty easily)
def songlyrics(song):
    '''Returns the lyrics found in songlyrics.com for the specified mp3 file or
    an empty string if not found'''
    translate = {
        URLESCAPE: "",
        " ": "-"
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    artist = re.sub(r'\-{2,}', '-', artist)
    title = re.sub(r'\-{2,}', '-', title)

    url = "http://www.songlyrics.com/{}/{}-lyrics".format(artist, title)
    soup = get_soup(url)
    text = soup.find(id='songLyricsDiv')
    if not text:
        return ""

    return text.getText().strip()

def lyricscom(song):
    '''Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found'''
    artist = song.artist.lower()
    artist = normalize(artist, " ", "+")
    title = song.title

    url = "https://www.lyrics.com/artist/{}".format(artist)
    soup = get_soup(url)
    location = ""
    for a in soup.select('tr a'):
        if a.string.lower() == title.lower():
            location = a['href']
            break
    if location == "":
        return ""

    url = "https://www.lyrics.com"+location
    soup = get_soup(url)
    body = soup.find(id="lyric-body-text")
    if not body:
        return ""

    return body.get_text().strip()

def vagalume(song):
    '''Returns the lyrics found in vagalume.com.br for the specified mp3 file or an
    empty string if not found'''
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

    url = "https://www.vagalume.com.br/{}/{}.html".format(artist, title)
    soup = get_soup(url)
    body = soup.select('div[itemprop="description"]')
    if body == []:
        return ""

    content = body[0]
    for br in content.find_all('br'):
        br.replace_with('\n')

    return content.get_text().strip()

def lyricsmode(song):
    '''Returns the lyrics found in lyricsmode.com for the specified mp3 file or an
    empty string if not found'''
    translate = {
        URLESCAPE: "",
        " ": "_"
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    artist = re.sub(r'\_{2,}', '_', artist)
    title = re.sub(r'\_{2,}', '_', title)

    if artist[0:4].lower() == "the ":
        artist = artist[4:]

    if artist[0:2].lower() == 'a ':
        prefix = artist[2]
    else:
        prefix = artist[0]

    url = "http://www.lyricsmode.com/lyrics/{}/{}/{}.html".format(prefix,
            artist, title)
    soup = get_soup(url)
    content = soup.find(id="lyrics_text")

    return content.get_text().strip()

def letras(song):
    '''Returns the lyrics found in letras.com for the specified mp3 file or an
    empty string if not found'''
    translate = {
        "&": "a",
        URLESCAPE: "",
        " ": "-"
    }
    artist = song.artist.lower()
    artist = normalize(artist, translate)
    title = song.title.lower()
    title = normalize(title, translate)

    url = "https://www.letras.com/{}/{}/".format(artist, title)
    soup = get_soup(url)
    content = soup.find('article')
    if not content:
        return ""

    text = ""
    for br in content.find_all('br'):
        br.replace_with('\n')

    for p in content.find_all('p'):
        text += p.get_text()

    return text.strip()

def musica(song):
    '''Returns the lyrics found in musica.com for the specified mp3 file or an
    empty string if not found'''
    safe = "?=:/"
    artist = song.artist.title()
    artist = normalize(artist)
    title = song.title.title()
    title = normalize(title.lower())

    url = "https://www.musica.com/letras.asp?t2="+artist
    soup = get_soup(url, safe=safe)
    first_res = soup.find(href=re.compile(r'https://www.musica.com/letras.asp\?letras=.*'))
    if first_res is None:
        return ""

    url = first_res['href']
    soup = get_soup(url, safe=safe)
    for a in soup.find_all('a'):
        if re.search(re.escape(title)+"$", a.text, re.IGNORECASE):
            first_res = a
            break
    else:
        return ""

    url = "https://www.musica.com/"+first_res['href']
    soup = get_soup(url, safe=safe)
    content = soup.p
    if not content:
        return ""

    for rem in content.find_all('font'):
        rem.unwrap()
    for googlead in content.find_all(['script', 'ins']):
        googlead.decompose()

    text = str(content)
    text = re.sub(r'<.?p>', '', text)
    text = re.sub(r'<.?br.?>', '\n', text)

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
    lyricscom,
    musica
]

def id_source(source, full=False):
    '''Returns the name of a website-scrapping function'''
    if source == azlyrics:
        name = "AZLyrics.com" if full else 'AZL'
    elif source == metrolyrics:
        name = "MetroLyrics.com" if full else 'MET'
    elif source == lyricswikia:
        name = "lyrics.wikia.com" if full else 'WIK'
    elif source == darklyrics:
        name = "DarkLyrics.com" if full else 'DAR'
    elif source == metalarchives:
        name = "Metal-archives.com" if full else 'ARC'
    elif source == genius:
        name = "Genius.com" if full else 'GEN'
    elif source == musixmatch:
        name = "Musixmatch.com" if full else 'XMA'
    elif source == songlyrics:
        name = "SongLyrics.com" if full else 'SON'
    elif source == vagalume:
        name = "Vagalume.com.br" if full else 'VAG'
    elif source == letras:
        name = "Letras.com" if full else 'LET'
    elif source == lyricsmode:
        name = "Lyricsmode.com" if full else 'LYM'
    elif source == lyricscom:
        name = "Lyrics.com" if full else 'LYC'
    elif source == musica:
        name = "Musica.com" if full else'MUS'
    else:
        name = ''

    return name

class Record:
    """Defines an entry in the stats 'database'. Packs a set of information
    about an execution of the scrapping functions. This class is auxiliary to
    Stats"""
    def __init__(self):
        self.successes = 0
        self.fails     = 0
        self.avg_time  = 0
        self.runtimes  = []

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"""Successes: {self.successes}
Fails: {self.fails}
Success rate: {self.success_rate():.2f}%
Average runtime: {Record.avg(self.runtimes):.2f}s"""

    def add_runtime(self, runtime):
        if runtime != 0:
            self.avg_time *= len(self.runtimes)
            self.avg_time += runtime
            self.runtimes.append(runtime)
            self.avg_time /= len(self.runtimes)

    def success_rate(self):
        if self.successes + self.fails == 0:
            success_rate = 0
        else:
            success_rate = (self.successes*100/(self.successes + self.fails))

        return success_rate

    @staticmethod
    def avg(values):
        """Returns the average of a list of numbers"""
        if values == []:
            return 0
        else:
            return sum(values)/len(values)

class Stats:
    """Stores a series of statistics about the execution of the program"""
    def __init__(self):
        # Maps every lyrics scraping function to a Record object
        self.source_stats = {}

        for name in sources:
            self.source_stats[name.__name__] = Record()

    def add_result(self, source, found, runtime):
        """Adds a new record to the statistics 'database'. This function is
        intended to be called after a website has been scraped. The arguments
        indicate the function that was called, the time taken to scrap the
        website and a boolean indicating if the lyrics were found or not
        """
        self.source_stats[source.__name__].add_runtime(runtime)
        if found:
            self.source_stats[source.__name__].successes += 1
        else:
            self.source_stats[source.__name__].fails += 1

    def avg_time(self, source=None):
        """Returns the average time taken to scrape lyrics. If a string or a
        function is passed as source, return the average time taken to scrape
        lyrics from that source, otherwise return the total average"""
        total = 0
        count = 0
        if source is None:
            runtimes = []
            for rec in self.source_stats.values():
                for runtime in rec.runtimes:
                    if runtime != 0:
                        runtimes.append(runtime)

            total = sum(runtimes)
            count = len(runtimes)
            if count == 0:
                return 0
            else:
                return total/count
        else:
            if callable(source):
                return self.source_stats[source.__name__].avg_time
            else:
                return self.source_stats[source].avg_time

    def print_stats(self):
        '''Print a series of relevant stats about a full execution. This function
        is meant to be called at the end of the program'''
        best = worst = fastest = slowest = ()
        found = 0
        total_time = 0
        for source, rec in self.source_stats.items():
            if not best or rec.successes > best[1]:
                best = (source, rec.successes, rec.success_rate())
            if not worst or rec.successes < worst[1]:
                worst = (source, rec.successes, rec.success_rate())

            avg = self.avg_time(source)
            if not fastest or (avg != 0 and avg < fastest[1]):
                fastest = (source, avg)
            if not slowest or (avg != 0 and avg > slowest[1]):
                slowest = (source, avg)

            found += rec.successes
            total_time += sum(rec.runtimes)

        # best_source = max([rec.successes for rec in self.source_stats.values()])
        # fastest_source = min([self.avg_time(source) for source in sources])
        # found = sum([rec.successes for rec in self.source_stats.values()])
        # total_time = sum([sum(rec.runtimes) for rec in self.source_stats.values()])

        # The songs which lyrics were not found, will be the number of fails
        # for the last source in the list
        notfound = self.source_stats[sources[-1].__name__].fails

        total_time = "%d:%02d:%02d" % (total_time/3600, (total_time/3600)/60, (total_time%3600)%60)
        string = f"""Total runtime: {total_time}
    Lyrics found: {found}
    Lyrics not found:{notfound}
    Most useful source: {best[0].capitalize()} ({best[1]} lyrics found)\
({best[2]:.2f}% success rate)
    Least useful source: {worst[0].capitalize()} ({worst[1]} lyrics found)\
({worst[2]:.2f}% success rate)
    Fastest website to scrape: {fastest[0].capitalize()} (Avg: {fastest[1]:.2f}s per search)
    Slowest website to scrape: {slowest[0].capitalize()} (Avg: {slowest[1]:.2f}s per search)
    Average time per website: {self.avg_time():.2f}s

xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxx    PER WEBSITE STATS:      xxx
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    """
        for source in sources:
            s = str(self.source_stats[source.__name__])
            string += f"\n{source.__name__.upper()}\n{s}\n"

        print(string)

class Song:
    def __init__(self):
        self.artist = ""
        self.title = ""
        self.album = ""
        self.lyrics = ""

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if self.artist and self.title and not hasattr(self, 'filename'):
            return f"{self.artist} - {self.title}"
        elif self.filename:
            return self.filename
        else:
            return ""

    @classmethod
    def from_filename(cls, filename):
        if not filename:
            logger.error("No filename specified")
            return None

        if not os.path.exists(filename):
            logger.error(f"Err: File '{filename}' not found")
            return None

        if os.path.isdir(filename):
            logger.error(f"Err: File '{filename}' is a directory")
            return None

        tags = eyed3.load(filename).tag
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
    def from_info(cls, artist, title, album=""):
        song = cls.__new__(cls)
        song.__init__()

        if not artist or not title:
            logger.error("Incomplete song info")
            return None

        song.artist = artist
        song.title = title
        song.album = album

        return song

    @classmethod
    def from_string(cls, name, separator='-', reverse=False):
        """Parse attributes from a string formatted as 'artist - title'"""
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

    @classmethod
    def from_string(cls, name, separator='-'):
        """Parse attributes from a string formatted as 'artist - title'"""
        song = cls.__new__(cls)
        recv = [t.strip() for t in name.split(separator)]
        if len(recv) < 2:
            sys.stderr.write('Wrong format!\n')
            return None

        song.artist = recv[0]
        song.title = ''.join(recv[1:])
        song.lyrics = ''

        return song

class Result:
    """Contains the results generated from run, so they can be returned as a
    single variable"""
    def __init__(self, song, source=None, runtimes={}):
        self.song = song

        # The source where the lyrics were found (or None if they weren't)
        self.source = source

        # A dictionary that maps every source to the time taken to scrape
        # the website. Keys corresponding to unused sources will be missing
        self.runtimes = runtimes

def exclude_sources(exclude, section=False):
    """Returns a narrower list of sources.
    If the exclude parameter is a list, every one of its items will be removed
    from the returned list.
    If it's just a function (or a function's name) and 'section' is set to
    False (default), a copy of the sources list without this element will be
    returned.
    If it's a function (or a function's name) but the section parameter is set
    to True, the returned list will be a section of the sources list, including
    everything between 'exclude' and the end of the list"""
    logger.debug('Wahttup')
    newlist = sources.copy()
    if type(exclude) is list:
        logger.debug('list')
        newlist = sources
        for source in exclude:
            if source in newlist:
                newlist = newlist.remove(source)
    elif callable(exclude):
        logger.debug('callable')
        if not section:
            newlist = newlist.remove(exclude)
        else:
            if exclude in newlist:
                pos = newlist.index(exclude)
                newlist = sources[pos:]
    elif type(exclude) is str:
        logger.debug('string')
        this_module = importlib.import_module(__name__)
        if hasattr(this_module, exclude):
            func = getattr(this_module, exclude)
            print(func)
            if not section:
                newlist = newlist.remove(exclude)
            else:
                if func in newlist:
                    pos = newlist.index(func)
                    newlist = sources[pos+1:]
    else:
        logger.debug('Something else')

    return newlist

def get_lyrics(song, sources=sources):
    """Searches for lyrics of a single song and returns a Result object with
    the various stats collected in the process.
    The optional parameter 'sources' specifies an alternative list of sources.
    If not present, the main list will be used"""

    if song.lyrics and not overwrite:
        logger.debug(f"'{song}' already has embedded lyrics")
        return None

    lyrics = ""
    start = 0
    end = 0
    runtimes = {}
    for source in sources:
        try:
            start = time.time()
            lyrics = source(song)
            end = time.time()
            runtimes[source] = end-start

            if lyrics != '':
                logger.info(f'++ {source.__name__}: Found lyrics for {song}\n')
                song.lyrics = lyrics
                return Result(song, source, runtimes)
            else:
                logger.info(f'-- {source.__name__}: Could not find lyrics for {song}\n')

        except (HTTPError, HTTPException, URLError, ConnectionError) as e:
            # logger.exception(f'== {source.__name__}: {e}\n')
            logger.info(f'-- {source.__name__}: Could not find lyrics for {song}\n')

        finally:
            end = time.time()
            runtimes[source] = end-start

    return Result(song, None, runtimes)

def run_mp(songs):
    '''Concurrently calls get_lyrics to fetch the lyrics of a large list of
    songs'''
    stats = Stats()
    if debug:
        good = open('found', 'w')
        bad = open('notfound', 'w')

    logger.debug(f"Launching a pool of {jobcount} processes")
    chunksize = math.ceil(len(songs)/os.cpu_count())
    try:
        with Pool(jobcount) as pool:
            for result in pool.imap_unordered(get_lyrics, songs, chunksize):
                if result is None: continue

                for source, runtime in result.runtimes.items():
                    stats.add_result(source, result.source == source, runtime)

                if result.source is not None:
                    if debug:
                        good.write(f"{id_source(source)}: {result.song}\n")
                        good.flush()

                    if hasattr(result.song, 'filename'):
                        audiofile = eyed3.load(result.song.filename)
                        audiofile.tag.lyrics.set(u''+result.song.lyrics)
                        audiofile.tag.save()
                        print("Lyrics added for "+str(result.song))
                    else:
                        print(f'''FROM {id_source(result.source, full=True)}

{result.song.lyrics}
-----------------------------------------------------------------------------\
''')
                else:
                    print(f"Lyrics for {result.song} not found")
                    if debug:
                        bad.write(str(result.song)+'\n')
                        bad.flush()

    finally:
        if debug:
            good.close()
            bad.close()

    return stats

def load_from_file(filename):
    '''Load a list of filenames from an external text file'''
    if os.path.isdir(filename):
        logger.error(f"Err: '{filename}' is a directory")
        return None
    if not os.path.isfile(filename):
        logger.error(f"Err: File '{filename}' does not exist")
        return None

    try:
        with open(filename, 'r') as sourcefile:
            songs = []
            for line in sourcefile:
                if line[-1] == '\n':
                    songs.append(line[0:-1])
                else:
                    songs.append(line)

        return songs
    except IOError as e:
        logger.exception(e)
        return None

jobcount = 1
overwrite = False
errno = 0
print_stats = False
debug = False

def parseargv():
    '''Parse command line arguments. Settings will be stored in the global
    variables declared above'''
    global jobcount
    global overwrite
    global errno
    global print_stats
    global debug

    parser = argparse.ArgumentParser(description="Find lyrics for a set of mp3"
            " files and embed them as metadata")
    parser.add_argument("-j", "--jobs", help="Number of parallel processes", type=int,
            metavar="N", default=1)
    parser.add_argument("-f", "--force", help="Confirm the use of too many processes",
            action="store_true")
    parser.add_argument("-o", "--overwrite", help="Overwrite lyrics of songs"
            " that already have them", action="store_true")
    parser.add_argument("-r", "--recursive", help="Recursively search for"
            " mp3 files", nargs='?', const='.')
    parser.add_argument("-n", "--by-name", help="A list of song names in"
            " 'artist - title' format", nargs='*')
    parser.add_argument("-s", "--stats", help="Print a series of statistics at"
            " the end of the execution", action="store_true")
    parser.add_argument("-v", "--verbose", help="Set verbosity level (pass it"
            " up to three times)", action="count")
    parser.add_argument("-d", "--debug", help="Enable debug output",
            action="store_true")
    parser.add_argument("--from-file", help="Read a list of files from a text"
            " file", type=str)
    parser.add_argument("files", help="The mp3 files to search lyrics for",
            nargs="*")
    args = parser.parse_args()

    overwrite = args.overwrite
    print_stats = args.stats

    if args.verbose is None or args.verbose == 0:
        logger.setLevel(logging.CRITICAL)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    if args.jobs:
        if args.jobs > os.cpu_count() and not args.force:
            logger.error("You specified a number of parallel threads"
            " greater than the number of processors in your system. To continue"
            " at your own risk you must confirm you choice with -f")
            errno = os.errno.EINVAL
            return None
        elif args.jobs <= 0:
            logger.error(f"{sys.argv[0]}: error: argument -j/--jobs should"
            " have a value greater than zero")
            errno = os.errno.EINVAL
            return None
        else:
            jobcount = args.jobs

    songs = set()
    if not args.by_name:
        mp3files = []
        if args.files:
            mp3files = args.files
        elif args.recursive:
            mp3files = glob.iglob(args.recursive+"/**/*.mp3", recursive=True)
        elif args.from_file:
            if not os.path.isfile(args.from_file):
                errno = os.errno.ENOENT
                return None

            mp3files = load_from_file(args.from_file)
            if not mp3files:
                logger.error('Err: Could not read from file')
                sys.stderr.write('Err: Could not read from file\n')
                errno = os.errno.EIO
                return None

        else:
            logger.error("Err: No files specified")
            sys.stderr.write("Err: No files specified\n")
            errno = os.errno.EINVAL
            return None

        songs = set([Song.from_filename(f) for f in mp3files])
    else:
        for song in args.by_name:
            songs.add(Song.from_string(song))

    # Just in case some song constructors failed, remove all the Nones
    return songs.difference({None})

def main():
    songs = parseargv()
    if songs is None:
        print (os.strerror(errno))
        return errno
    elif len(songs) == 0:
        print('No songs specified')
        return 0
    else:
        print(songs)

    logger.debug("Running with "+str(songs))
    try:
        start = time.time()
        stats = run_mp(songs)
        end = time.time()
        if print_stats:
            stats.print_stats()

        total_time = end-start
        total_time = "%d:%02d:%02d" % (total_time/3600, (total_time/3600)/60, (total_time%3600)%60)
        print(f"Total time: {total_time}")

    except KeyboardInterrupt:
        print("Interrupted")

    return 0

if __name__ == '__main__':
    exit(main())
