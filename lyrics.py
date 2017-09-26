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
import re
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
    req = urllib.Request(url, headers={"User-Agent": "foobar"})
    response = urllib.urlopen(req)
    return BeautifulSoup(response.read(), 'html.parser')

def metrolyrics(mp3file):
    '''Returns the lyrics found in metrolyrics for the specified mp3 file or an
    empty string if not found'''
    title = mp3file.tag.title
    artist = mp3file.tag.artist
    title = title.lower().replace(' ', '-')
    artist = artist.lower().replace(' ', '-')

    url="http://www.metrolyrics.com/{}-lyrics-{}.html".format(title, artist)
    soup = bs(url)
    body = soup.find(id="lyrics-body-text").find_all('p')
    text = ""
    for verse in body:
        text += verse.get_text()
        if verse != body[-1]:
            text+='\n\n'

    return text.strip()

def darklyrics(mp3file):
    '''Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.lower().replace(' ', '')
    album = mp3file.tag.album
    album = album.lower().replace(' ', '')
    title = mp3file.tag.title

    url="http://www.darklyrics.com/lyrics/{}/{}.html".format(artist, album)
    soup = bs(url)
    text = ""
    for header in soup.find_all('h3'):
        song = str(header.get_text())
        next_sibling = header.next_sibling
        if song.lower().find(title.lower()) != -1:
            while next_sibling.name is None or next_sibling.name != 'h3':
                if next_sibling.name is None:
                    text+=str(next_sibling)
                next_sibling = next_sibling.next_sibling

    return text.strip()

def azlyrics(mp3file):
    '''Returns the lyrics found in azlyrics for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.lower().replace(' ', '')
    title = mp3file.tag.title
    title = title.lower().replace(' ', '')

    url="https://www.azlyrics.com/lyrics/{}/{}.html".format(artist, title)
    soup = bs(url)
    body = soup.find_all('div', class_="")[-1]
    return body.get_text().strip()

def genius(mp3file):
    '''Returns the lyrics found in genius.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.capitalize().replace(' ', '-')
    title = mp3file.tag.title
    title = title.lower().replace(' ', '-')

    url="https://www.genius.com/{}-{}-lyrics".format(artist, title)
    soup = bs(url)
    return soup.p.get_text().strip()

# IMPROVE THIS. Use this query to get a json with the ID of the song:
# http://www.metal-archives.com/search/ajax-advanced/searching/songs/?songTitle={title}&;bandName={artist}&ExactBandMatch=1
def metalarchives(mp3file):
    '''Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.capitalize().replace(' ', '_')
    album = mp3file.tag.album
    album = album.capitalize().replace(' ', '_')
    trackno = mp3file.tag.track_num[0]

    url="https://www.metal-archives.com/albums/{}/{}/".format(artist, album)
    soup = bs(url)
    song_id = soup.select('.table_lyrics tr.odd,tr.even')[trackno].a['name']
    url="https://www.metal-archives.com/release/ajax-view-lyrics/id/{}".format(song_id)
    soup = bs(url)
    return soup.get_text().strip()

def lyricswikia(mp3file):
    '''Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.title().replace(' ', '_')
    title = mp3file.tag.title
    title = title.title().replace(' ', '_')

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
    artist = mp3file.tag.artist
    artist = artist.title().replace(' ', '-')
    title = mp3file.tag.title
    title = title.title().replace(' ', '-')

    url="https://www.musixmatch.com/lyrics/{}/{}".format(artist, title)
    soup = bs(url)
    text = ""
    for p in soup.find_all('p', class_='mxm-lyrics__content '):
        text+=p.get_text()

    return text.strip()

def lyricscom(mp3file):
    '''Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.title().replace(' ','%20')
    title = mp3file.tag.title

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
    artist = mp3file.tag.artist
    artist = artist.lower().replace(' ', '-')
    title = mp3file.tag.title
    title = title.lower().replace(' ', '-')

    url="https://www.vagalume.com.br/{}/{}.html".format(artist, title)
    soup = bs(url)
    content = soup.select('div[itemprop="description"]')
    if content == []:
        return ""

    main = content[0]
    for br in main.find_all('br'):
        br.replace_with('\n')

    return main.get_text().strip()

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

def letrasmus(mp3file):
    '''Returns the lyrics found in letras.mus.br for the specified mp3 file or an
    empty string if not found'''
    artist = mp3file.tag.artist
    artist = artist.lower().replace(' ', '-')
    title = mp3file.tag.title
    title = title.lower().replace(' ', '-')

    url="https://www.letras.mus.br/{}/{}/".format(artist, title)
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
    artist = mp3file.tag.artist
    artist = artist.title().replace(' ', '+')
    title = mp3file.tag.title.lower()

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
    text = re.sub('<.?p>','',text)
    text = re.sub('<.?br.?>','\n', text)

    return text.strip()


songs = glob.iglob("**.mp3", recursive=True)
for filename in songs:
    try:
        audiofile = eyed3.load(filename)
        lyrics=""

        sources = [
            azlyrics,
            metrolyrics,
            lyricswikia,
            darklyrics,
            metalarchives,
            genius,
            musixmatch,
            vagalume,
            letrasmus,
            lyricsmode,
            musica,
            lyricscom
        ]
        for source in sources:
            try:
                lyrics = source(audiofile)
                if lyrics != '':
                    break
            except HTTPError as e:
                pass
            except Exception as e:
                pass
        else:
            sys.stderr.write('Could not find lyrics for ' + filename + '\n')
            continue

        # audiofile.tag.lyrics.set(u''+lyrics)
        print("=== {} - {}".format(audiofile.tag.artist, audiofile.tag.title))
        # audiofile.tag.save()
        print(lyrics)
        # print("Lyrics added")

    except Exception as e:
        print (e)
        sys.stderr.write('Err: Could not add lyrics for '+filename + '\n')
