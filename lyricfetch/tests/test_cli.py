from lyricfetch import Result
from lyricfetch import Song
from lyricfetch.cli import process_result
from conftest import tag_mp3

def test_process_result(mp3file):
    """
    Check that the `process_result()` function can write the lyrics to the
    corresponding mp3 and return wheter or not they were found.
    """
    artist = 'lör'
    title = 'requiem'
    song_lyrics = 'hello world'
    tag_mp3(mp3file, artist=artist, title=title)
    song = Song.from_filename(mp3file)
    song.lyrics = song_lyrics

    result_notfound = Result(song=song, source=None, runtimes={})
    assert not process_result(result_notfound)
    assert not Song.from_filename(mp3file).lyrics

    result_found = Result(song=song, source='whatever', runtimes={})
    assert process_result(result_found)
    assert Song.from_filename(mp3file).lyrics == song_lyrics
