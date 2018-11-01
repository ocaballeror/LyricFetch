"""
Init.
"""
import os
import json
import logging
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

__version__ = '1.1.1'

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Discard eyed3 messages unless they're important
logging.getLogger('eyed3.mp3.headers').setLevel(logging.CRITICAL)

from . import scraping
sources = [
    scraping.azlyrics,
    scraping.metrolyrics,
    scraping.lyricswikia,
    scraping.darklyrics,
    scraping.metalarchives,
    scraping.genius,
    scraping.musixmatch,
    scraping.songlyrics,
    scraping.vagalume,
    scraping.letras,
    scraping.lyricsmode,
    scraping.lyricscom
]

from .run import Result
from .song import Song
from .run import exclude_sources, get_lyrics
from .song import get_current_song
from .stats import Stats
