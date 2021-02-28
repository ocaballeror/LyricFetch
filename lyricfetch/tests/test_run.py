"""
Main tests module.
"""
import asyncio
import shutil
import tempfile

import lyricfetch.run
from lyricfetch import CONFIG
from lyricfetch import Song
from lyricfetch import get_lyrics
from lyricfetch import get_song_lyrics
from conftest import tag_mp3


def sync_lyrics(song):
    """
    Synchronously get lyrics for a song.
    """
    return asyncio.run(get_song_lyrics(song))


# TODO: monkeypatch sources here so we don't connect to the outside
def test_getlyrics_from_info():
    """
    Check that the main method can actually return a result with lyrics.
    """
    song = Song(artist='Iron maiden', title='Hallowed be thy name')
    result = sync_lyrics(song)
    assert 'hallowed be thy name' in result.song.lyrics.lower()


# TODO: monkeypatch sources here so we don't connect to the outside
def test_getlyrics_from_song(mp3file):
    """
    Check that the main method can find the lyrics for a song and write them as
    ID3 metadata.
    """
    tag_mp3(mp3file, artist='YOB', title='Our raw heart')
    song = Song.from_filename(mp3file)
    result = sync_lyrics(song)
    assert 'my restless ghost' in result.song.lyrics.lower()


def test_getlyrics_dont_overwrite(mp3file):
    """
    Check that we skip a song if the mp3 file already has embedded lyrics.
    """
    placeholder = 'Some lyrics'
    tag_mp3(mp3file, lyrics=placeholder)

    song = Song.from_filename(mp3file)
    CONFIG['overwrite'] = False
    assert sync_lyrics(song) is None
    assert song.lyrics == placeholder


# TODO: monkeypatch sources here so we don't connect to the outside
def test_getlyrics_overwrite(mp3file):
    """
    Check that we can overwrite the lyrics of a song if it already has them.
    """
    placeholder = 'Some lyrics'
    tag_mp3(mp3file, artist='Baroness', title='Eula', lyrics=placeholder)

    song = Song.from_filename(mp3file)
    CONFIG['overwrite'] = True
    result = sync_lyrics(song)
    assert result.song.lyrics != placeholder
    assert 'forget the taste of my own tongue' in result.song.lyrics.lower()


def test_get_lyrics(mp3file, monkeypatch):
    """
    Test the process() function when passing multiple songs. This time it
    should call get_lyrics() for each song in the collection.
    """
    song_lyrics = 'some lyrics here'

    async def fake_scraper(*_):
        return song_lyrics

    async def gather(coro):
        return [res async for res in coro]

    other_mp3 = tempfile.mktemp()
    shutil.copy(mp3file, other_mp3)
    mp3files = [mp3file, other_mp3]
    songs = [Song.from_filename(f) for f in mp3files]
    monkeypatch.setattr(lyricfetch.run, 'sources', [fake_scraper])
    results = asyncio.run(gather(get_lyrics(songs)))
    assert set(songs) == set(res.song for res in results)

    for result in results:
        assert result.source is fake_scraper
        assert result.song.lyrics == song_lyrics
