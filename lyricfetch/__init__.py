import os


CONFFILE = '../config.json'
CONFIG = {
    'jobcount': 1,
    'overwrite': False,
    'errno': 0,
    'print_stats': False,
    'debug': False,
    'lastfm_key': ''
}
for key in CONFIG:
    environ_key = 'LFETCH_' + key.upper()
    if environ_key in os.environ:
        print(environ_key)
        CONFIG[key] = os.environ.get(environ_key)

# Contains the characters usually removed or replaced in URLS
URLESCAPE = '.¿?%_@,;&\\/()\'"-!¡'
URLESCAPES = URLESCAPE + ' '

__version__ = '1.0.0'

from .lyrics import Song, Stats, Result
from .lyrics import azlyrics, metrolyrics, lyricswikia, darklyrics
from .lyrics import metalarchives, genius, musixmatch, songlyrics
from .lyrics import vagalume, letras, lyricsmode, lyricscom
from .lyrics import exclude_sources, get_lastfm, get_lyrics, id_source
