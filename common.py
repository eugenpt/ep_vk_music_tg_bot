import asyncio
import requests

from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache



def de_async(fun, *args, **kwargs):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        print('No loop')
        loop = None
        # return asyncio.run(fun(*args, **kwargs))
        # try:
        #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # except:
        #     pass
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
    if loop and loop.is_running():
        print('loop and running')
        # return asyncio.run_coroutine_threadsafe(fun(*args, **kwargs), loop).result()
        return asyncio.gather(
            fun(*args, **kwargs)
        ).result() # this seems wrong, what if there are no results awailable?
    else:
        print('loop not running')
        return asyncio.run(fun(*args, **kwargs))
        # return loop.run_until_complete(
        #     fun(*args, **kwargs)
        # )

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