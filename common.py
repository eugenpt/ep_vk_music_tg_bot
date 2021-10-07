import asyncio
import logging
import requests

from asyncio.coroutines import iscoroutine
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

logger = logging.getLogger("ep." + __name__)

def de_async(fun, *args, **kwargs):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.debug('No loop')
        # loop = None
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except:
            pass
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if iscoroutine(fun):
        cor = fun
    else:
        cor = fun(*args, **kwargs)
    if loop and loop.is_running():
        logger.debug('loop and running')
        # return asyncio.run_coroutine_threadsafe(fun(*args, **kwargs), loop).result()
        return asyncio.gather(cor).result() # this seems wrong, what if there are no results awailable?
    else:
        logger.debug('loop not running')
        # return asyncio.run(fun(*args, **kwargs))
        return loop.run_until_complete(cor)

@lru_cache(maxsize=32)
def download_url(url):
    return requests.get(url).content

def download_urls(urls):
    with ThreadPoolExecutor(max_workers=3) as executor:
        return executor.map(download_url, urls)


def time_str(dur):
    rs = ''
    was = 0
    for d in [3600,60,1]:
        if was:
            rs = rs+':%02i' % int(dur/d)
        else:
            if dur > d:
                rs = rs + '%i' % int(dur/d)

                was = 1
        dur = dur % d

    return rs