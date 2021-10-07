#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 15:27:05 2021

@author: ep
"""

# %%

import binascii
import io
import logging
import os
import re
import requests
import vk_api

from Crypto.Cipher import AES
from functools import lru_cache
from pydub import AudioSegment
from threading import Thread, Event
from time import sleep, time
from vk_api import audio

from auths import AUTHS
from common import de_async, time_str, download_url, download_urls

# %%

logger = logging.getLogger(__name__)

DEBUG = {}

# %%
vk_session = None
vk_audio = None

REPORT_PERC_EVERY_S = 3

# vk_session = vk_api.VkApi(login=AUTHS[0], password=AUTHS[1])
# vk_session.auth()
# vk = vk_session.get_api()  # Теперь можно обращаться к методам API как к обычным
# vk_audio = audio.VkAudio(vk_session)  # Получаем доступ к audio

# %%

def log(*args):
    logger.log(*args)

def info(*args):
    logger.info(*args)

vk_audio_id_sep = '|'
vk_audio_id_sep = ':'
def vk_audio_id_encode(a,b):
    return str(a) + vk_audio_id_sep + str(b)

def vk_audio_id_decode(x):
    return x.split(vk_audio_id_sep)

ep_vk_audio_by_ids__saved = {}

def prep_audio(r):
    if r['duration']:
        r['duration_str'] = time_str(r['duration'])
        r['title_str'] = ('⏳' if is_m3u8(r['url']) else '') +\
                         r['artist']+' - '+r['title']+'  '+ r['duration_str']
    else:
        r['title_str'] = r['artist']+' - '+r['title']+'  '+ r['duration_str']
        r['duration_str'] = '??:??'

    r['ids_string'] = vk_audio_id_encode(r['owner_id'],str(r['id']))

    global ep_vk_audio_by_ids__saved
    ep_vk_audio_by_ids__saved[r['ids_string']] = r

    return r

@lru_cache(maxsize=128)
def ep_vk_search(q, n_results_per_page=10, page=0):
    global vk_audio
    return [prep_audio(a) for a in vk_audio.search(q, n_results_per_page, page*n_results_per_page)]

def ep_vk_audio_by_ids(ids):
    if ids in ep_vk_audio_by_ids__saved:
        return ep_vk_audio_by_ids__saved[ids]
    else:
        return ep_vk_audio_by_ids__request(ids)

def ep_vk_audio_by_ids__request(ids):
    global vk_audio
    owner_id,audio_id=[int(js) for js in vk_audio_id_decode(ids)]
    return prep_audio(vk_audio.get_audio_by_id(owner_id, audio_id))


def download_audio(url, log_fun=info):
    info('downloading audio from [%s]..' % url)
    log_fun('скачиваю аудио..')

    if is_m3u8(url):
        content = download_m3u8(url, log_fun=log_fun)
    else:
        content = download_url(url)# requests.get(url).content

    size_str = "~%.1fMB" % (len(content)/(1024*1024))
    log_fun(size_str+'..')

    return content





def is_m3u8(url):
    return url.find('index.m3u8')>=0


def download_m3u8(url, log_fun=info, _async=True):
    info("loading m3u8..")

    log_fun("будет долго..")

    R = requests.get(url)

    root_url = R.url[:R.url.find('index.m3u8')]
    m3u8_content = R.content.decode()

    content = b''

    parts = parse_m3u8_parts(m3u8_content, root_url=root_url)
    print('got parts info and keys, getting parts..')

    if _async:
        print('going async..')
        content = download_m3u8_parts(parts)
    else:
        last_perc_report_time = time()
        for j,part in enumerate(parts):
            part_content = requests.get(part['url']).content
            content = content + decrypt_m3u8_part_content(part, part_content)

            if (log_fun is not None
                and time()-last_perc_report_time > REPORT_PERC_EVERY_S):
                last_perc_report_time = time()
                log_fun('%i%%..' % (100.0 * j / len(parts)))
    
    return convert_to_mp3(content)

def convert_to_mp3(content):
    tfile = io.BytesIO(content)
    audio = AudioSegment.from_file(tfile)
    
    outfile = io.BytesIO()
    audio.export(outfile, format="mp3")
    return outfile.read()

def decrypt_m3u8_part_content(part, content):
    if part['key'] is None:
        return content
    else:
        iv = binascii.a2b_hex('%032x' % part['j'])
        DEBUG['part'] = part
        DEBUG['part']['content_pre'] = content
        return AES.new(
            part['key'],
            AES.MODE_CBC,
            iv
        ).decrypt(content)


def parse_m3u8_parts(m3u8_content, root_url=None):
    if root_url is None:
        root_url = ''

    LS = m3u8_content.split('\n')
    j = 0

    R = []

    key = None
    key_url = None
    for line_j,line in enumerate(LS):
        if len(line) > 0:
            if line[0]=='#':
                if line.find('#EXT-X-KEY')==0:
                    method = re.match('.+METHOD=([^,]+)',line).groups()[0]

                    if method == 'NONE':
                        key = None
                        key_url = None
                    elif method == 'AES-128':
                        key_url = re.match('.+URI="(.+)"',line).groups()[0]
                        # I thought about making this async as well, no real win
                        key = download_url(key_url)
                    else:
                        raise ValueError('?? method=[%s]' % method)
            else:
                j = j + 1

                R.append({
                    'url': root_url + line,
                    'key': key,
                    'key_url': key_url,
                    'j': j
                })

    return R

def download_m3u8_parts(parts):
    content = b''
    contents = download_urls([part['url'] for part in parts])
    for j, part_content in enumerate(contents):
        content = content + decrypt_m3u8_part_content(parts[j], part_content)
    return content


def download_cover(cover_urls, log_fun=info):
    log_fun('обложка..')

    exc_str = None
    for cover_url in cover_urls:
        try:
            thumb = requests.get(cover_url, timeout=10).content
            log_fun('ок..')
            return thumb
        except:
            exc_str = traceback.format_exc()
            pass

    log_fun('ошибка..')
    log(exc_str)
    # send_exc(query.message, exc_str)

    return None


def renew_connection():
    global vk_session
    global vk_audio
    global AUTHS
    info('renewing vk_session..')
    vk_session = vk_api.VkApi(login=AUTHS[0], password=AUTHS[1])
    vk_session.auth()
    vk = vk_session.get_api()  # Теперь можно обращаться к методам API как к обычным
    vk_audio = audio.VkAudio(vk_session)  # Получаем доступ к audio
    info('done')

def renew_connection_threadfun(interval_s, stop_event, check_every_s=1):
    while True:
        for j in range(int(interval_s/check_every_s)):
            if stop_event.isSet():
                break
            sleep(check_every_s)

        if stop_event.isSet():
            break

        renew_connection()

    info('renewing stopped.')

global vk_renew_stop
vk_renew_stop = Event()
def ep_vk_finish():
    global vk_renew_stop
    vk_renew_stop.set()


# %%
# aaa
renew_thread = Thread(target=renew_connection_threadfun, args=(3600,vk_renew_stop), daemon=False)
renew_thread.start()
info('renewing thread started..')
renew_connection()
# %%

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    if vk_audio is None:
        renew_connection()

    R_audios = ep_vk_search('taylor swift story of us')

    m3u8 = None
    for tr in R_audios:
        if 'm3u8' in tr['url']:
            m3u8 = tr

            url = m3u8['url']
            url = 'https://psv4.vkuseraudio.net/audio/ee/H0TweWen2yfqf7RHlc1O2zJ7umj-gi77cCOsLQ/5dNjs1PjA_PTI5/08cD5GajxZeVxGWlg/index.m3u8?extra=hKnmI91hEWS0ah7icbhDNjShGhQfUTqkACZUkC19A6i1jyHYVIZPeNs9teNTcqilUVgJDb4Gqql3432Kv6sx6xxUQ9954Bb0ACf9uEeOmG-kPpYlrlmOSfjq3C-V-iFHWK182ZepWk7FibS4JGuarcVDKg'

            url = 'https://psv4.vkuseraudio.net/audio/ee/_EplxK1EqK15cmttGdXDv2TiD4nuRw5LKsoc9g/d4NTgwMjYyMzM2/9aQUtpYG56c1RxbV0/index.m3u8?extra=N7yTDJhzW9G5g-gu5GAnbX0vmj4s_zWBcj8u7zOgDlWNNj3ZsKXb9FKLhWM96MalQFRQivNKouIaW7GL8jOLmehRsaqBZjqvbJtD1_vCA70cGKG79yez83Iop5Go4MQyd7WKqB_a6epbCmKjMX_FOKTI_eo'
            tstart = time()

            R = requests.get(url)

            root_url = R.url[:R.url.find('index.m3u8')]
            m3u8_content = R.content.decode()

            content = b''

            parts = parse_m3u8_parts(m3u8_content, root_url=root_url)

            content = download_m3u8_parts(parts)

            with open('D:\\temp2.mp3', 'wb') as f:
                f.write(content)
            print('async, with async keys: %.2fs' % (time()-tstart))
            
            tstart = time()
            content = download_m3u8(url, _async=True)
            print('(async=True) requests: %.2fs' % (time()-tstart))

            with open('D:\\temp1.mp3', 'wb') as f:
                f.write(content)
            tstart = time()
            content = download_m3u8(url, _async=False)
            print('usual requests: %.2fs' % (time()-tstart))

            with open('D:\\temp3.mp3', 'wb') as f:
                f.write(content)
            break

    aaa
    try:
        while 1:
            sleep(1)
    except :
        pass
    finally:
        ep_vk_finish()

    pass
