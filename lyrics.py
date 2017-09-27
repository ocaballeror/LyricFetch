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
# lyricsmode.com      X
# metal-archives.com  X
# letras.mus.br       X
# musica.com          X

import sys
import os
import time
import re
import argparse
import glob
import eyed3
import logging
import urllib.request as urllib

from urllib.error import HTTPError
from bs4 import NavigableString, Tag, BeautifulSoup

logging.getLogger("eyed3.mp3.headers").setLevel(logging.CRITICAL)

def bs(url):
    '''Requests the specified url and returns a BeautifulSoup object with its
    contents'''
    url = urllib.quote(url,safe=":/")
    print('URL: '+url)
    sys.stdout.flush()
    req = urllib.Request(url, headers={"User-Agent": "foobar"})
    response = urllib.urlopen(req)
    return BeautifulSoup(response.read(), 'html.parser')

# Contains the characters usually removed or replaced in URLS
urlescape = ".¿?_@,;&\\/()'\"-!¡"
urlescapeS = ' '+urlescape
def normalize(string, charsToRemove='', replacement=''):
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
        'ú': 'u',
        'ü': 'u'
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
    artist = mp3file.tag.artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)

    url="http://www.metrolyrics.com/{}-lyrics-{}.html".format(title, artist)
    soup = bs(url)
    body = soup.find(id="lyrics-body-text")
    if body is None:
        return ""

    text = ""
    body = body.find_all('p')
    for verse in body:
        text += verse.get_text()
        if verse != body[-1]:
            text+='\n\n'

    return text.strip()

def darklyrics(mp3file):
    '''Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.lower()
    artist = normalize(artist, urlescapeS, '')
    album = mp3file.tag.album.lower()
    album = normalize(album, urlescapeS, '')
    title = mp3file.tag.title

    url="http://www.darklyrics.com/lyrics/{}/{}.html".format(artist, album)
    soup = bs(url)
    text = ""
    for header in soup.find_all('h3'):
        song = str(header.get_text())
        next_sibling = header.next_sibling
        if song.lower().find(title.lower()) != -1:
            while next_sibling is not None and (next_sibling.name is None\
                or next_sibling.name != 'h3'):
                if next_sibling.name is None:
                    text+=str(next_sibling)
                next_sibling = next_sibling.next_sibling

    return text.strip()

def azlyrics(mp3file):
    '''Returns the lyrics found in azlyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.lower()
    if artist[0:2] == "a ":
        artist = artist[2:]
    artist = normalize(artist, urlescapeS, "")
    title = mp3file.tag.title.lower()
    title = normalize(title, urlescapeS, "")


    url="https://www.azlyrics.com/lyrics/{}/{}.html".format(artist, title)
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
    artist = mp3file.tag.artist.capitalize()
    artist = normalize(artist, translate)
    title = mp3file.tag.title.capitalize()
    title = normalize(title, translate)

    url="https://www.genius.com/{}-{}-lyrics".format(artist, title)
    soup = bs(url)
    return soup.p.get_text().strip()

# IMPROVE THIS. Use this query to get a json with the ID of the song:
# http://www.metal-archives.com/search/ajax-advanced/searching/songs/?songTitle={title}&;bandName={artist}&ExactBandMatch=1
def metalarchives(mp3file):
    '''Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.capitalize()
    artist = normalize(artist, ' ', '_')
    album = mp3file.tag.album.capitalize()
    album = normalize(album, ' ', '_')
    trackno = mp3file.tag.track_num[0]

    url="https://www.metal-archives.com/albums/{}/{}/".format(artist, album)
    soup = bs(url)
    song_ids = soup.select('.table_lyrics tr.odd,tr.even')
    if not song_ids:
        return ''

    song_id = song_ids[trackno-1].a['name']
    url="https://www.metal-archives.com/release/ajax-view-lyrics/id/{}".format(song_id)
    soup = bs(url)
    return soup.get_text().strip()

def lyricswikia(mp3file):
    '''Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.title()
    artist = normalize(artist, ' ', '_')
    title = mp3file.tag.title
    title = normalize(title, ' ', '_')

    url="https://lyrics.wikia.com/wiki/{}:{}".format(artist, title)
    soup = bs(url)
    text=""
    content = soup.find('div', class_='lyricbox')
    for unformat in content.findChildren(['i','b']):
        unformat.unwrap()
    for remove in content.findChildren('div'):
        remove.decompose()

    nlcount=0
    for line in content.children:
        if line is None or line=='<br/>' or line=='\n':
            if nlcount==2:
                text+="\n\n"
                nlcount=0
            else:
                nlcount+=1
        else:
            nlcount=0
            text+=str(line).replace('<br/>','\n')
    return text.strip()

def musixmatch(mp3file):
    '''Returns the lyrics found in musixmatch for the specified mp3 file or an
    empty string if not found'''
    escape = re.sub("'-¡¿",'',urlescape)
    translate = {
        escape: "",
        " ": "-"
    }
    artist = mp3file.tag.artist.title()
    artist = re.sub(r"( '|' )", "", artist)
    artist = re.sub(r"'", "-", artist)
    title = mp3file.tag.title
    title = re.sub(r"( '|' )", "", title)
    title = re.sub(r"'", "-", title)

    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url="https://www.musixmatch.com/lyrics/{}/{}".format(artist, title)
    soup = bs(url)
    text = ""
    for p in soup.find_all('p', class_='mxm-lyrics__content '):
        text+=p.get_text()

    return text.strip()

def lyricscom(mp3file):
    '''Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.lower()
    artist = normalize(artist, " ", "+")
    title = mp3file.tag.title.lower()
    title = normalize(title, " ", "+")

    url="https://www.lyrics.com/artist/{}".format(artist)
    soup = bs(url)
    location=""
    for a in soup.select('tr a'):
        if a.string.lower() == title.lower():
            location = a['href']
            break
    if location == "":
        return ""

    url="https://www.lyrics.com"+location
    soup = bs(url)
    body = soup.find(id="lyric-body-text")
    return body.get_text().strip()

def vagalume(mp3file):
    '''Returns the lyrics found in vagalume.com.br for the specified mp3 file or an
    empty string if not found'''
    translate = {
        '@': 'a',
        urlescape: '',
        ' ': '-'
    }
    artist = mp3file.tag.artist.lower()
    artist = normalize(artist, translate)
    artist = re.sub(r'\-{2,}', '-', artist)
    title = mp3file.tag.title.lower()
    title = normalize(title, translate)
    title = re.sub(r'\-{2,}', '-', title)

    url="https://www.vagalume.com.br/{}/{}.html".format(artist, title)
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
    artist = mp3file.tag.artist
    artist = artist.lower().replace(' ', '_')
    title = mp3file.tag.title
    title = title.lower().replace(' ', '_')

    url="http://www.lyricsmode.com/lyrics/{}/{}/{}.html".format(artist[0],
            artist, title)
    print(url)
    soup = bs(url)
    content = soup.find(id="lyrics_text")

    return content.get_text().strip()

def letras(mp3file):
    '''Returns the lyrics found in letras.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.lower()
    artist = normalize(artist, "_@,;&\\/\"\'", "")
    artist = normalize(artist, " ", "-")
    title = mp3file.tag.title.lower()
    title = normalize(title, "_@,;&\\/\"", "_")

    url="https://www.letras.com/{}/{}/".format(artist, title)
    soup = bs(url)
    content = soup.find('article')
    text=""
    for br in content.find_all('br'):
        br.replace_with('\n')

    for p in content.find_all('p'):
        text+=p.get_text()

    return text.strip()

def musica(mp3file):
    '''Returns the lyrics found in musica.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist.title()
    artist = normalize(artist)
    title = mp3file.tag.title
    title = normalize(title.lower())

    url="https://www.musica.com/letras.asp?t2={}".format(artist)
    print(url)
    soup = bs(url)
    first_res = soup.find(href=re.compile('https://www.musica.com/letras.asp\?letras=.*'))
    if first_res is None:
        return ""

    url=first_res['href']
    print(url)
    soup = bs(url)
    for a in soup.find_all('a'):
        if re.search(title+"$", a.text, re.IGNORECASE):
            first_res = a
            break
    else:
        print('Not found')
        return ""

    url = "https://www.musica.com/"+first_res['href']
    print(url)
    soup = bs(url)
    content = soup.p
    for rem in content.find_all('font'):
        rem.unwrap()
    for googlead in content.find_all(['script', 'ins']):
        googlead.decompose()

    text = str(content)
    text = re.sub(r'<.?p>','',text)
    text = re.sub(r'<.?br.?>','\n', text)

    return text.strip()



# sources = [
#     azlyrics,
#     metrolyrics,
#     lyricswikia,
#     darklyrics,
#     metalarchives,
#     genius,
#     musixmatch,
#     vagalume,
#     letrasmus,
#     lyricsmode,
#     musica,
#     lyricscom
# ]
sources = [
        azlyrics,
        metrolyrics,
        lyricswikia,
        darklyrics,
        metalarchives,
        genius,
        musixmatch,
        vagalume
]

class Stats:
    def __init__(self):
        # Stores how many songs have been found on every source
        self.source_count = {}
        # Stores a list of the time in seconds that took to scrape
        # lyrics from every site in every successful attempt
        self.source_times = {}

        for name in sources:
            self.source_count[name.__name__] = 0
            self.source_times[name.__name__] = []

    def add_result(self, source, runtime):
        """Adds a new record to the statistics 'database'"""
        self.source_count[source.__name__]+=1
        self.source_times[source.__name__].append(runtime)

    def avg(self, values):
        """Returns the average of a list of numbers"""
        return sum(values)/len(values)

    def avg_time(self, source=None):
        """Returns the average time taken to scrape lyrics. If a string or a
        function is passed as source, return the average time taken to scrape
        lyrics from this source"""
        total=0
        count=0
        if source is None:
            for runtime in self.source_times.values():
                total+=sum(runtime)
                count+=len(runtime)
            return total/count
        else:
            if callable(source):
                return self.avg(self.source_times[source.__name___])
            else:
                return self.avg(self.source_times[source])

    def fastest_source(self):
        """Returns the name of the source with the lowest average scrape time"""
        min([self.avg_time(source) for source in sources])

    def best_source(self):
        """Returns the name of the source with the most lyrics found"""
        max(self.source_count.values())

def run(songs):
    good = open('found', 'w')
    bad = open('notfound', 'w')
    for filename in songs:
        print(filename)
        if not os.path.exists(filename):
            sys.stderr.write(filename + " not found\n")
            continue
        if os.path.isdir(filename):
            sys.stderr.write(filename + " is a directory\n")
            continue
        try:
            audiofile = eyed3.load(filename)
            lyrics=""
            found = False

            for source in sources:
                try:
                    lyrics = source(audiofile)
                    if lyrics != '':
                        sys.stderr.write(f'++ {source.__name__}: Found lyrics for {filename}\n')
                        sys.stderr.flush()
                        good.write(filename+'\n')
                        good.flush()
                        found = True
                        break
                    else:
                        sys.stderr.write('-- '+source.__name__+': Could not find lyrics for ' + filename + '\n')
                        sys.stderr.flush()
                except HTTPError as e:
                    sys.stderr.write(f'== {source.__name__}: {e}\n')
                    sys.stderr.flush()
                    pass
                # except Exception as e:
                #     sys.stderr.write(f'== {source.__name__}: {e}\n')
                #     sys.stderr.flush()
                #     pass
            else:
                if not found:
                    sys.stderr.write('XX Nobody found find lyrics for ' + filename + '\n')
                    sys.stderr.flush()
                    bad.write(filename+'\n')
                    bad.flush()
                    continue

            # audiofile.tag.lyrics.set(u''+lyrics)
            # print("=== {} - {}".format(audiofile.tag.artist, audiofile.tag.title))
            # audiofile.tag.save()
            # print(lyrics)
            # print("Lyrics added for "+filename)
        except IOError:
            sys.stderr.write(f'Err: Could not operate with file: {filename}\n')
        # except Exception as e:
        #     print (e)
        #     sys.stderr.write('Err: Could not add lyrics for '+filename + '\n')
    close(good)
    close(bad)


jobcount=0
stats=False
mp3files=[]

def parseargv():
    '''Parse command line arguments. Settings will be stored in the global
    variables declared above'''
    parser = argparse.ArgumentParser(description="Find lyrics for a set of mp3"
            " files and embed them as metadata")
    # group = parser.add_mutually_exclusive_group()
    parser.add_argument("-j", "--jobs", help="Number of parallel processes", type=int,
            default=0)
    parser.add_argument("-f", "--force", help="Confirm the use of too many processes",
            action="store_true")
    parser.add_argument("-s", "--stats", help="Output some stats about the"
            " execution at the end", action="store_true")
    parser.add_argument("-r", "--recursive", help="Recursively search for all"
            " the mp3 files in the current directory", action="store_true")
    parser.add_argument("--from-file", help="Read a list of files from a text"
            " file", type=str)
    parser.add_argument("files", help="The mp3 files to search lyrics for",
            nargs="*")
    args = parser.parse_args()

    if args.jobs:
        if args.jobs > os.cpu_count() and not args.force:
            sys.stderr.write("You specified a number of parallel threads"
            " greater than the number of processors in your system. To continue"
            " at your own risk you must confirm you choice with -f\n")
            return 1
        jobcount = args.jobs

    # Argsparse would not let me create a mutually exclusive group with
    # positional arguments, so I made the checking myself
    if args.files and args.recursive:
        parser.print_usage(sys.stderr)
        sys.stderr.write(f"{sys.argv[0]}: error: argument -r/--recursive: not"
                " allowed with positional arguments")
        return 2

    mp3files = []
    if args.files:
        mp3files = args.files
    elif args.recursive:
        mp3files = glob.glob("**/*.mp3", recursive=True)
    elif args.from_file:
        with open(args.from_file, 'r') as sourcefile:
            for line in sourcefile:
                if line[-1] == '\n':
                    mp3files.append(line[0:-1])
                else:
                    mp3files.append(line)
    else:
        sys.stderr.write("Err: No files specified\n")
        return 2

    print(mp3files)
    return mp3files

# Yes I know this is not the most pythonic way to do things, but it helps me
# organize my code.
def main():
    ret = parseargv()
    if type(ret) == int and ret != 0:
        return ret

    start = time.time()
    print ("Running with "+str(mp3files))
    try:
        run(ret)
    except KeyboardInterrupt:
        print ("Interrupted")
    elapsed = time.time() - start
    output = "%d:%02d:%02d" % (elapsed/3600,(elapsed/3600)/60,(elapsed%3600)%60)
    print (output)
    sys.stderr.write(output+'\n')

    return 0

if __name__=='__main__':
    exit(main())
