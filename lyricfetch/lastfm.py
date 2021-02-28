from . import CONFIG
from . import logger
from .scraping import get_url


async def get_lastfm(method, lastfm_key='', **kwargs):
    """
    Request the specified method from the lastfm api.
    """
    if not lastfm_key:
        if 'lastfm_key' not in CONFIG or not CONFIG['lastfm_key']:
            logger.warning('No lastfm key configured')
            return None
        else:
            lastfm_key = CONFIG['lastfm_key']

    url = 'http://ws.audioscrobbler.com/2.0/?method={}&api_key={}&format=json'
    url = url.format(method, lastfm_key)
    for key in kwargs:
        url += '&{}={}'.format(key, kwargs[key])

    response = await get_url(url, parser='json')
    if 'error' in response:
        logger.error('Error number %d in lastfm query: %s',
                     response['error'], response['message'])
        return None

    return response
