#/usr/bin/env python3

# Find lyrics for all the .mp3 files in the current directory
# and write them as metadata for the files
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
import glob
import eyed3
import logging
import urllib.request as urllib

from urllib.error import *
from http.client import HTTPException
from bs4 import NavigableString, Tag, BeautifulSoup
from multiprocessing import Pool

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Send verbose logs to a log file
debuglogger = logging.FileHandler('debuglog', 'w')
debuglogger.setLevel(logging.DEBUG)
logger.addHandler(debuglogger)

# Send error logs to an errlog file
errlogger = logging.FileHandler('errlog', 'w')
errlogger.setLevel(logging.WARNING)
logger.addHandler(errlogger)

# Discard eyed3 messages unless they're important
logging.getLogger("eyed3.mp3.headers").setLevel(logging.CRITICAL)

def bs(url, safe=":/"):
    '''Requests the specified url and returns a BeautifulSoup object with its
    contents'''
    url = urllib.quote(url,safe=safe)
    logger.debug('URL: '+url)
    req = urllib.Request(url, headers={"User-Agent": "foobar"})
    response = urllib.urlopen(req)
    return BeautifulSoup(response.read(), 'html.parser')

# Contains the characters usually removed or replaced in URLS
urlescape = ".¿?%_@,;&\\/()'\"-!¡"
urlescapeS = ' '+urlescape
def normalize(string, charsToRemove=None, replacement=''):
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

    if isinstance(charsToRemove, dict):
        for chars,replace in charsToRemove.items():
            reg = "["+re.escape(chars)+"]"
            ret = re.sub(reg, replace, ret)

    elif isinstance(charsToRemove, str):
        reg = '['+re.escape(charsToRemove)+']'
        ret = re.sub(reg, replacement, ret)

    return ret

def metrolyrics(mp3file):
    '''Returns the lyrics found in metrolyrics for the specified mp3 file or an
    empty string if not found'''
    translate = {urlescape: "", " ":"-"}
    title = mp3file.tag.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)

    url = "http://www.metrolyrics.com/{}-lyrics-{}.html".format(title, artist)
    soup = bs(url)
    body = soup.find(id="lyrics-body-text")
    if body is None:
        return ""

    text = ""
    body = body.find_all('p')
    for verse in body:
        text += verse.get_text()
        if verse != body[-1]:
            text += '\n\n'

    return text.strip()

def darklyrics(mp3file):
    '''Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, urlescapeS, '')
    album = mp3file.tag.album.lower()
    album = normalize(album, urlescapeS, '')
    title = mp3file.tag.title

    url = "http://www.darklyrics.com/lyrics/{}/{}.html".format(artist, album)
    soup = bs(url)
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

def azlyrics(mp3file):
    '''Returns the lyrics found in azlyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.album_artist.lower()
    if artist[0:2] == "a ":
        artist = artist[2:]
    artist = normalize(artist, urlescapeS, "")
    title = mp3file.tag.title.lower()
    title = normalize(title, urlescapeS, "")


    url = "https://www.azlyrics.com/lyrics/{}/{}.html".format(artist, title)
    soup = bs(url)
    body = soup.find_all('div', class_="")[-1]
    return body.get_text().strip()

def genius(mp3file):
    '''Returns the lyrics found in genius.com for the specified mp3 file or an
    empty string if not found'''
    translate = {
        '@': 'at',
        '&': 'and',
        urlescape: '',
        ' ': '-'
    }
    artist = mp3file.tag.album_artist.capitalize()
    artist = normalize(artist, translate)
    title = mp3file.tag.title.capitalize()
    title = normalize(title, translate)

    url = "https://www.genius.com/{}-{}-lyrics".format(artist, title)
    soup = bs(url)
    for content in soup.find_all('p'):
        if content:
            text = content.get_text().strip()
            if text:
                return text

    return ''

def metalarchives(mp3file):
    '''Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.album_artist.capitalize()
    artist = normalize(artist, ' ', '_')
    title = mp3file.tag.title.capitalize()
    title = normalize(title, ' ', '_')

    url = "http://www.metal-archives.com/search/ajax-advanced/searching/songs/"
    url += f"?songTitle={title}&bandName={artist}&ExactBandMatch=1"
    soup = bs(url)
    links = soup.find_all('a')
    for link in links:
        song_id = re.search(r'lyricsLink_([0-9]*)', str(link))
        if song_id:
            song_id = song_id.group(1)
        else:
            continue

        url="https://www.metal-archives.com/release/ajax-view-lyrics/id/{}".format(song_id)
        try:
            soup = bs(url)
            text = soup.get_text()
            if re.search('lyrics not available', text):
                return ""
            else:
                return text.strip()
        except (HTTPError, URLError):
            continue

    return ""

def lyricswikia(mp3file):
    '''Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.album_artist.title()
    artist = normalize(artist, ' ', '_')
    title = mp3file.tag.title
    title = normalize(title, ' ', '_')

    url = "https://lyrics.wikia.com/wiki/{}:{}".format(artist, title)
    soup = bs(url)
    text = ""
    content = soup.find('div', class_='lyricbox')
    if not content:
        return ""

    for unformat in content.findChildren(['i','b']):
        unformat.unwrap()
    for remove in content.findChildren('div'):
        remove.decompose()

    nlcount = 0
    for line in content.children:
        if line is None or line=='<br/>' or line=='\n':
            if nlcount==2:
                text += "\n\n"
                nlcount = 0
            else:
                nlcount += 1
        else:
            nlcount = 0
            text += str(line).replace('<br/>', '\n')
    return text.strip()

def musixmatch(mp3file):
    '''Returns the lyrics found in musixmatch for the specified mp3 file or an
    empty string if not found'''
    escape = re.sub("'-¡¿", '', urlescape)
    translate = {
        escape: "",
        " ": "-"
    }
    artist = mp3file.tag.album_artist.title()
    artist = re.sub(r"( '|' )", "", artist)
    artist = re.sub(r"'", "-", artist)
    title = mp3file.tag.title
    title = re.sub(r"( '|' )", "", title)
    title = re.sub(r"'", "-", title)

    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url = "https://www.musixmatch.com/lyrics/{}/{}".format(artist, title)
    soup = bs(url)
    text = ""
    for p in soup.find_all('p', class_='mxm-lyrics__content '):
        text += p.get_text()

    return text.strip()

# Songlyrics is basically a mirror for musixmatch, so it helps us getting
# around musixmatch's bot detection (they block IPs pretty easily)
def songlyrics(mp3file):
    '''Returns the lyrics found in songlyrics.com for the specified mp3 file or
    an empty string if not found'''
    translate = {
        urlescape: "",
        " ": "-"
    }
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, translate)
    title = mp3file.tag.title.lower()
    title = normalize(title, translate)

    artist = re.sub(r'\-{2,}', '-', artist)
    title = re.sub(r'\-{2,}', '-', title)

    url = "http://www.songlyrics.com/{}/{}-lyrics".format(artist, title)
    soup = bs(url)
    text = soup.find(id='songLyricsDiv')
    if not text:
        return ""

    return text.getText().strip()

def lyricscom(mp3file):
    '''Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, " ", "+")
    title = mp3file.tag.title

    url = "https://www.lyrics.com/artist/{}".format(artist)
    soup = bs(url)
    location=""
    for a in soup.select('tr a'):
        if a.string.lower() == title.lower():
            location = a['href']
            break
    if location == "":
        return ""

    url = "https://www.lyrics.com"+location
    soup = bs(url)
    body = soup.find(id="lyric-body-text")
    if not body:
        return ""

    return body.get_text().strip()

def vagalume(mp3file):
    '''Returns the lyrics found in vagalume.com.br for the specified mp3 file or an
    empty string if not found'''
    translate = {
        '@': 'a',
        urlescape: '',
        ' ': '-'
    }
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = mp3file.tag.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url = "https://www.vagalume.com.br/{}/{}.html".format(artist, title)
    soup = bs(url)
    body = soup.select('div[itemprop="description"]')
    if body == []:
        return ""

    content = body[0]
    for br in content.find_all('br'):
        br.replace_with('\n')

    return content.get_text().strip()

def lyricsmode(mp3file):
    '''Returns the lyrics found in lyricsmode.com for the specified mp3 file or an
    empty string if not found'''
    translate = {
        urlescape: "",
        " ": "_"
    }
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, translate)
    title = mp3file.tag.title.lower()
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
    soup = bs(url)
    content = soup.find(id="lyrics_text")

    return content.get_text().strip()

def letras(mp3file):
    '''Returns the lyrics found in letras.com for the specified mp3 file or an
    empty string if not found'''
    translate = {
        "&": "a",
        urlescape: "",
        " ": "-"
    }
    artist = mp3file.tag.album_artist.lower()
    artist = normalize(artist, translate)
    title = mp3file.tag.title.lower()
    title = normalize(title, translate)

    url = "https://www.letras.com/{}/{}/".format(artist, title)
    soup = bs(url)
    content = soup.find('article')
    if not content:
        return ""

    text = ""
    for br in content.find_all('br'):
        br.replace_with('\n')

    for p in content.find_all('p'):
        text += p.get_text()

    return text.strip()

def musica(mp3file):
    '''Returns the lyrics found in musica.com for the specified mp3 file or an
    empty string if not found'''
    safe = "?=:/"
    artist = mp3file.tag.album_artist.title()
    artist = normalize(artist)
    title = mp3file.tag.title.title()
    title = normalize(title.lower())

    url = "https://www.musica.com/letras.asp?t2="+artist
    soup = bs(url, safe=safe)
    first_res = soup.find(href=re.compile(r'https://www.musica.com/letras.asp\?letras=.*'))
    if first_res is None:
        return ""

    url = first_res['href']
    soup = bs(url, safe = safe)
    for a in soup.find_all('a'):
        if re.search(re.escape(title)+"$", a.text, re.IGNORECASE):
            first_res = a
            break
    else:
        return ""

    url = "https://www.musica.com/"+first_res['href']
    soup = bs(url, safe=safe)
    content = soup.p
    if not content:
        return ""

    for rem in content.find_all('font'):
        rem.unwrap()
    for googlead in content.find_all(['script', 'ins']):
        googlead.decompose()

    text = str(content)
    text = re.sub(r'<.?p>','',text)
    text = re.sub(r'<.?br.?>','\n', text)

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

def id_source(source):
    if source == azlyrics:
        return 'AZL'
    elif source == metrolyrics:
        return 'MET'
    elif source == lyricswikia:
        return 'WIK'
    elif source == darklyrics:
        return 'DAR'
    elif source == metalarchives:
        return 'ARC'
    elif source == genius:
        return 'GEN'
    elif source == musixmatch:
        return 'XMA'
    elif source == songlyrics:
        return 'SON'
    elif source == vagalume:
        return 'VAG'
    elif source == letras:
        return 'LET'
    elif source == lyricsmode:
        return 'LYM'
    elif source == lyricscom:
        return 'LYC'
    elif source == musica:
        return 'MUS'


def avg(values):
    """Returns the average of a list of numbers"""
    if values == []:
        return 0
    else:
        return sum(values)/len(values)

class Record:
    """Defines an entry in the stats 'database'. Packs a set of information
    about an execution of the scrapping functions. This class is auxiliary to
    Stats"""
    def __init__(self):
        self.successes = 0
        self.fails     = 0
        self.avg_time  = 0
        self.runtimes  = []

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
            success_rate = (self.successes*100/(self.successes + self.fails)       )

        return success_rate

    def __str__(self):
        return f"""Successes: {self.successes}
Fails: {self.fails}
Success rate: {self.success_rate():.2f}%
Average runtime: {avg(self.runtimes):.2f}s"""

    def __repr__(self):
        return self.__str__()

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
        best = None
        worst = None
        fastest = None
        slowest = None
        sr = None
        found = 0
        notfound = 0
        total_time = 0
        for source,rec in self.source_stats.items():
            if best is None or rec.successes > best[1]:
                best = (source, rec.successes, rec.success_rate())
            if worst is None or rec.successes < worst[1]:
                worst = (source, rec.successes, rec.success_rate())

            avg = self.avg_time(source)
            if fastest is None or (avg != 0 and avg < fastest[1]):
                fastest = (source, avg)
            if slowest is None or (avg != 0 and avg > slowest[1]):
                slowest = (source, avg)

            found += rec.successes
            total_time += sum(rec.runtimes)

        # best_source = max([rec.successes for rec in self.source_stats.values()])
        # fastest_source = min([self.avg_time(source) for source in sources])
        # found = sum([rec.successes for rec in self.source_stats.values()])
        # total_time = sum([sum(rec.runtimes) for rec in self.source_stats.values()])
        total_time = "%d:%02d:%02d" % (total_time/3600,(total_time/3600)/60,(total_time%3600)%60)
        notfound = len(mp3files) - found
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

    PER WEBSITE STATS:
    """
        for source in sources:
            s = str(self.source_stats[source.__name__])
            string += f"\n{source.__name__.upper()}\n{s}\n"

        print(string)

class Mp_res:
    """Contains the results generated from run_mp, so they can be returned as a
    single variable"""
    def __init__(self, source=None, filename="", runtimes={}):

        # The source where the lyrics were found (or None if they weren't)
        self.source = source

        # The name of the file whose lyrics we were looking for
        self.filename = filename

        # A dictionary that maps every source to the time taken to scrape
        # the website. Keys corresponding to unused sources will be missing
        self.runtimes = runtimes

def run_mp(filename):
    """Searches for lyrics of a single song and returns an mp_res object with
    the various stats collected in the process. It is intended to be an
    auxiliary function to run, which will invoke it as a parallel process"""
    logger.info(filename)
    if not os.path.exists(filename):
        logger.error(f"Err: File '{filename}' not found")
        return None
    if os.path.isdir(filename):
        logger.error(f"Err: File '{filename}' is a directory")
        return None

    audiofile = eyed3.load(filename)
    if not audiofile:
        logger.warning(f"W: File '{filename}' could not be proccess as an mp3")
        return None

    if ''.join([l.text for l in audiofile.tag.lyrics]) and not overwrite:
        logger.debug(f"{filename} already has embedded lyrics")
        return None

    lyrics = ""
    start = 0
    end = 0
    runtimes = {}
    for source in sources:
        try:
            start = time.time()
            lyrics = source(audiofile)
            end = time.time()
            runtimes[source] = end-start

            if lyrics != '':
                logger.info(f'++ {source.__name__}: Found lyrics for {filename}\n')

                audiofile.tag.lyrics.set(u''+lyrics)
                audiofile.tag.save()
                return Mp_res(source, filename, runtimes)
            else:
                logger.info('-- '+source.__name__+': Could not find lyrics for ' + filename + '\n')

        except (HTTPError, HTTPException, URLError, ConnectionError) as e:
            # if not hasattr(e, 'code') or e.code != 404:
            #     logger.exception(f'== {source.__name__}: {e}\n')

            logger.info('-- '+source.__name__+': Could not find lyrics for ' + filename + '\n')

        finally:
            end = time.time()
            runtimes[source] = end-start

    return Mp_res(None, filename, runtimes)

def run(songs):
    stats = Stats()
    good = open('found', 'w')
    bad  = open('notfound', 'w')

    logger.debug("Launching a pool of "+str(jobcount)+" processes")
    chunksize = math.ceil(len(songs)/os.cpu_count())
    try:
        with Pool(jobcount) as pool:
            for result in pool.imap_unordered(run_mp, songs, chunksize):
                if result is None: continue

                for source, runtime in result.runtimes.items():
                    stats.add_result(source, result.source == source, runtime)

                if result.source is not None:
                    print("Lyrics added for "+result.filename)
                    good.write(f"{id_source(source)}: result.filename\n")
                    good.flush()
                else:
                    print(f"Lyrics for {result.filename} not found")
                    bad.write(result.filename+'\n')
                    bad.flush()

    finally:
        good.close()
        bad.close()

    return stats

def from_file(filename):
    '''Load a list of filenames from an external text file'''
    if os.path.isdir(filename):
        logger.error(f"Err: '{filename}' is a directory")
        return None
    if not os.path.isfile(filename):
        logger.error(f"Err: File '{filename}' does not exist")
        return None

    try:
        with open(filename, 'r') as sourcefile:
            mp3files = []
            for line in sourcefile:
                if line[-1] == '\n':
                    mp3files.append(line[0:-1])
                else:
                    mp3files.append(line)

        return mp3files
    except Exception as e:
        print(e)
        return None

jobcount = 1
mp3files = []
overwrite = False

def parseargv():
    '''Parse command line arguments. Settings will be stored in the global
    variables declared above'''
    global jobcount
    global mp3files
    global overwrite

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
    parser.add_argument("--from-file", help="Read a list of files from a text"
            " file", type=str)
    parser.add_argument("files", help="The mp3 files to search lyrics for",
            nargs="*")
    args = parser.parse_args()
    print(args)

    if args.jobs:
        if args.jobs > os.cpu_count() and not args.force:
            logger.error("You specified a number of parallel threads"
            " greater than the number of processors in your system. To continue"
            " at your own risk you must confirm you choice with -f")
            return 1
        elif args.jobs <= 0:
            logger.error(f"{sys.argv[0]}: error: argument -j/--jobs should"
            " have a value greater than zero")
            return 1
        else:
            jobcount = args.jobs

    if args.overwrite:
        overwrite = args.overwrite

    # Argsparse would not let me create a mutually exclusive group with
    # positional arguments, so I made the checking myself
    if args.files and args.recursive:
        parser.print_usage(sys.stderr)
        logger.error(f"{sys.argv[0]}: error: argument -r/--recursive: not"
                " allowed with positional arguments")
        return 2

    if args.files:
        mp3files = args.files
    elif args.recursive:
        mp3files = glob.glob(args.recursive+"/**/*.mp3", recursive=True)
    elif args.from_file:
        mp3files = from_file(args.from_file)
        if not mp3files:
            logger.error('Err: Could not read from file')
            return 2
    else:
        logger.error("Err: No files specified")
        return 2

    return 0

# Yes I know this is not the most pythonic way to do things, but it helps me
# organize my code.
def main():
    ret = parseargv()
    if ret != 0:
        return ret
    print(overwrite)

    logger.debug("Running with "+str(mp3files))
    try:
        start = time.time()
        stats = run(mp3files)
        end = time.time()
        stats.print_stats()
        total_time = end-start
        total_time = "%d:%02d:%02d" % (total_time/3600,(total_time/3600)/60,(total_time%3600)%60)
        print (f"Total time: {total_time}")

    except KeyboardInterrupt:
        print ("Interrupted")

    return 0

if __name__=='__main__':
    exit(main())
