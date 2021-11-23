"""
Scraping functions.
"""
import json
import re
from operator import attrgetter

import httpx
from bs4 import BeautifulSoup

from . import URLESCAPE
from . import URLESCAPES


async def get_url(url, parser='html'):
    """
    Requests the specified url and returns a BeautifulSoup object with its
    contents.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    response.raise_for_status()
    content = response.text
    if parser == 'html':
        return BeautifulSoup(content, 'html.parser', from_encoding='utf-8')
    elif parser == 'json':
        return json.loads(content)
    elif parser == 'raw':
        return content
    raise ValueError('Unrecognized parser')


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


async def darklyrics(song):
    """
    Returns the lyrics found in darklyrics for the specified mp3 file or an
    empty string if not found.
    """

    # Darklyrics relies on the album name
    if not hasattr(song, 'album') or not song.album:
        await song.fetch_album_name()
        if not hasattr(song, 'album') or not song.album:
            # If we don't have the name of the album, there's nothing we can do
            # on darklyrics
            return None

    artist = song.artist.lower()
    artist = normalize(artist, URLESCAPES, '')
    album = song.album.lower()
    album = normalize(album, URLESCAPES, '')
    title = song.title

    url = 'http://www.darklyrics.com/lyrics/{}/{}.html'.format(artist, album)
    soup = await get_url(url)
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


async def azlyrics(song):
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
    soup = await get_url(url)
    paragraphs = map(attrgetter('text'), soup.find_all('div', class_=''))
    text = '\n\n'.join(paragraphs).strip()
    return text


async def genius(song):
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
    soup = await get_url(url)

    # old style page
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        if not p:
            continue

        text = p.get_text().strip()
        if text:
            return text

    # new style page
    else:
        for div in soup.find_all('div'):
            classes = div.attrs.get('class', [])

            if any(klass.startswith('Lyrics__Container') for klass in classes):
                for br in div.find_all('br'):
                    br.replace_with('\n')

                return ''.join(div.contents)

    return None


async def metalarchives(song):
    """
    Returns the lyrics found in MetalArchives for the specified mp3 file or an
    empty string if not found.
    """
    artist = normalize(song.artist)
    title = normalize(song.title)

    url = 'https://www.metal-archives.com/search/ajax-advanced/searching/songs'
    url += f'/?songTitle={title}&bandName={artist}&ExactBandMatch=1'
    soup = await get_url(url, parser='json')
    if not soup:
        return None

    song_id_re = re.compile(r'lyricsLink_([0-9]*)')
    ids = set(re.search(song_id_re, a) for sub in soup['aaData'] for a in sub)
    if not ids:
        return None

    if None in ids:
        ids.remove(None)
    ids = map(lambda a: a.group(1), ids)
    for song_id in ids:
        url = 'https://www.metal-archives.com/release/ajax-view-lyrics/id/{}'
        lyrics = await get_url(url.format(song_id), parser='html')
        lyrics = lyrics.get_text().strip()
        if not re.search('lyrics not available', lyrics):
            return lyrics

    return None


async def lyricswikia(song):
    """
    Returns the lyrics found in lyrics.wikia.com for the specified mp3 file or
    an empty string if not found.
    """
    artist = song.artist.title()
    artist = normalize(artist, ' ', '_')
    title = song.title
    title = normalize(title, ' ', '_')

    url = 'https://lyrics.wikia.com/wiki/{}:{}'.format(artist, title)
    soup = await get_url(url)
    text = ''
    content = soup.find('div', class_='lyricbox')
    if not content:
        return None

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


async def musixmatch(song):
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
    soup = await get_url(url)
    text = ''
    contents = soup.find_all('p', class_='mxm-lyrics__content')
    for p in contents:
        text += p.get_text().strip()
        if p != contents[-1]:
            text += '\n\n'

    return text.strip()


# Songlyrics is basically a mirror for musixmatch, so it helps us getting
# around musixmatch's bot detection (they block IPs pretty easily)
async def songlyrics(song):
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
    soup = await get_url(url)
    text = soup.find(id='songLyricsDiv')
    if not text:
        return None

    text = text.getText().strip()
    if not text or text.lower().startswith('we do not have the lyrics for'):
        return None

    return text


async def lyricscom(song):
    """
    Returns the lyrics found in lyrics.com for the specified mp3 file or an
    empty string if not found.
    """
    artist = song.artist.lower()
    artist = normalize(artist, ' ', '+')

    url = 'https://www.lyrics.com/artist/{}'.format(artist)
    soup = await get_url(url)
    artist_page = ''
    for link in soup.select('tr a.name'):
        title = link.attrs.get('title')
        if not title:
            continue

        if normalize(title).lower() == normalize(song.artist).lower():
            artist_page = link.attrs['href']
            break
    else:
        return None

    url = 'https://www.lyrics.com/' + artist_page
    soup = await get_url(url)
    songs = soup.select('div.tdata-ext td a')
    for link in songs:
        if not link.string:
            continue

        if normalize(link.string.lower()) == normalize(song.title.lower()):
            song_page = link.attrs['href']
            break
    else:
        return None

    url = 'https://www.lyrics.com/' + song_page
    soup = await get_url(url)
    body = soup.find(id='lyric-body-text')
    if not body:
        return None

    return body.get_text().strip()


async def vagalume(song):
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
    soup = await get_url(url)
    body = soup.select('div#lyrics')
    if body == []:
        return None

    content = body[0]
    for br in content.find_all('br'):
        br.replace_with('\n')

    return content.get_text().strip()


async def lyricsmode(song):
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
    soup = await get_url(url)
    content = soup.find(id='lyrics_text')
    for div in content.find_all('div'):
        div.decompose()

    return content.get_text().strip()


async def letras(song):
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
    soup = await get_url(url)
    if not soup:
        return None

    found_title = soup.select_one('div.cnt-head_title h1')
    if not found_title:
        # The site didn't find lyrics and took us to the homepage
        return None

    found_title = found_title.get_text()
    found_title = re.sub(r'[\W_]+', '', found_title.lower())
    if found_title != re.sub(r'[\W_]+', '', song.title.lower()):
        # The site took us to the wrong song page
        return None

    content = soup.find('article')
    if not content:
        return None

    text = ''
    for br in content.find_all('br'):
        br.replace_with('\n')

    for p in content.find_all('p'):
        text += p.get_text() + '\n\n'

    return text.strip()


source_ids = {
    azlyrics: ('AZL', 'AZLyrics.com'),
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
        return None

    if full:
        return source_ids[source][1]
    else:
        return source_ids[source][0]
