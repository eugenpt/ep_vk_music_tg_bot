#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 15:27:05 2021

@author: ep
"""

# %%

import os
import requests
import vk_api

from threading import Thread, Event
from time import sleep
from vk_api import audio

from auths import *

# %%

vk_session = None
vk_audio = None

# vk_session = vk_api.VkApi(login=AUTHS[0], password=AUTHS[1])
# vk_session.auth()
# vk = vk_session.get_api()  # Теперь можно обращаться к методам API как к обычным 
# vk_audio = audio.VkAudio(vk_session)  # Получаем доступ к audio

# %%


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



def renew_connection(interval_s, stop_event):
    global vk_session
    global vk_audio
    global AUTHS
    while True:
        print('renewing..')
        vk_session = vk_api.VkApi(login=AUTHS[0], password=AUTHS[1])
        vk_session.auth()
        vk = vk_session.get_api()  # Теперь можно обращаться к методам API как к обычным 
        vk_audio = audio.VkAudio(vk_session)  # Получаем доступ к audio
        
        for j in range(int(interval_s/5)):
            if stop_event.isSet():
                break
            sleep(5)
        if stop_event.isSet():
            break
    print('renewing stopped.')

global vk_renew_stop
vk_renew_stop = Event()
def ep_vk_finish():
    global vk_renew_stop
    vk_renew_stop.set()
    

# %%
# aaa
renew_thread = Thread(target=renew_connection, args=(3600,vk_renew_stop), daemon=False)
renew_thread.start()
print('aaa')
# %%

if __name__ == "__main__":
    R_audios = ep_vk_search('taylor swift story of us')
    print(R_audios)
    try:
        while 1:
            sleep(1)
    except :
        pass
    finally:
        ep_vk_finish()
    
    pass    