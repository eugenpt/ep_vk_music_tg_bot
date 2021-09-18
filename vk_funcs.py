#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 15:27:05 2021

@author: ep
"""

# %%

import binascii
import logging
import os
import re
import requests
import vk_api

from Crypto.Cipher import AES
from threading import Thread, Event
from time import sleep
from vk_api import audio

from auths import *

# %%

logger = logging.getLogger(__name__)

# %%
vk_session = None
vk_audio = None

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
vk_audio_id_sep = '='
def vk_audio_id_encode(a,b):
    return str(a) + vk_audio_id_sep + str(b)

def vk_audio_id_decode(x):
    return x.split(vk_audio_id_sep)


def ep_vk_search(q, n_results_per_page=10, page=0):
    global vk_audio
    return list(vk_audio.search(q, n_results_per_page, page*n_results_per_page))
    

def ep_vk_audio_by_ids(ids):
    global vk_audio
    owner_id,audio_id=[int(js) for js in vk_audio_id_decode(ids)]
    return vk_audio.get_audio_by_id(owner_id, audio_id)


def download_audio(url):
    if 'index.m3u8' not in url:
        return requests.get(url).content
    else:
        return download_m3u8(url)        
        
def download_m3u8(url):
    info("loading m3u8..")
    R = requests.get(url)
    
    root_url = R.url[:R.url.find('index.m3u8')]
    m3u_content = R.content.decode()
    
    key = None
    content = b''
    
    j = 0
    for line in m3u_content.split('\n'):
        if len(line) > 0 and line[0]=='#':
            if line.find('#EXT-X-KEY')==0:
                method = re.match('.+METHOD=([^,]+)',line).groups()[0]
                
                if method == 'NONE':
                    key = None
                elif method == 'AES-128':
                    key_url = re.match('.+URI="(.+)"',line).groups()[0]
                    key = requests.get(key_url).content
                else:
                    raise ValueError('?? method=[%s]' % method)
        else:
            j = j + 1
            part_url = root_url + line
            
            part = requests.get(part_url).content
            
            if key is None:
                part_decrypted = part
            else:
                iv = binascii.a2b_hex('%032x' % j)
                part_decrypted = AES.new(key, AES.MODE_CBC, iv).decrypt(part)
        
            content = content + part_decrypted    
    
    return content

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
    if vk_audio is None:
        renew_connection()
    
    R_audios = ep_vk_search('taylor swift story of us')
    
    m3u8 = None
    for tr in R_audios:
        if 'm3u8' in tr['url']:
            m3u8 = tr
            
            content = download_m3u8(m3u8['url'])
            with open('D:\\temp2.mp3', 'wb') as f:
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