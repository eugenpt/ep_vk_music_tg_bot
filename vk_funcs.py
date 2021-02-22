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
from vk_api import audio

from auths import *

# %%

vk_session = vk_api.VkApi(login=AUTHS[0], password=AUTHS[1])
vk_session.auth()
vk = vk_session.get_api()  # Теперь можно обращаться к методам API как к обычным 
                                        # классам
vk_audio = audio.VkAudio(vk_session)  # Получаем доступ к audio

# %%

# id=765784


def ep_vk_search(q, n_results_per_page=10, page=0):
    
    return list(vk_audio.search(q, n_results_per_page, page*n_results_per_page))
    

def ep_vk_audio_by_ids(ids):
    owner_id,audio_id=[int(js) for js in ids.split('|')]
    return vk_audio.get_audio_by_id(owner_id, audio_id)

# %%

if __name__ == "__main__":
    R_audios = ep_vk_search('taylor swift story of us')
    print(R_audios)
    pass    