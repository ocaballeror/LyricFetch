import os
import json
from pathlib import Path


def _load_config():
    here = Path(os.path.realpath(__file__))
    config_name = here.parent / 'config.json'
    if config_name.is_file():
        with open(config_name) as config_file:
            CONFIG.update(json.load(config_file))

    for key in CONFIG:
        environ_key = 'LFETCH_' + key.upper()
        if environ_key in os.environ:
            CONFIG[key] = os.environ.get(environ_key)


# Contains the characters usually removed or replaced in URLS
URLESCAPE = '.¿?%_@,;&\\/()\'"-!¡'
URLESCAPES = URLESCAPE + ' '
CONFIG = {
    'jobcount': 1,
    'overwrite': False,
    'errno': 0,
    'print_stats': False,
    'debug': False,
    'lastfm_key': ''
}

_load_config()

__version__ = '1.0.2'

from .lyrics import Song, Stats, Result
from .lyrics import azlyrics, metrolyrics, lyricswikia, darklyrics
from .lyrics import metalarchives, genius, musixmatch, songlyrics
from .lyrics import vagalume, letras, lyricsmode, lyricscom
from .lyrics import exclude_sources, get_lastfm, get_lyrics, id_source
