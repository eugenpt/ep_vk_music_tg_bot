# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s
"""


#%%% imports

from os.path import exists
import pickle

#%%%

#%%% 

class PersistentData:
    USER_PLAYLISTS = {} # per user
    VK_AUDIOS = {} # including telegram file_ids (!)
    
    def __init__(self, _path=None):
        self.path =_path or self.get_path()
        self.load()
    
    def __del__(self):
        self.save()

    def load(self):
        R = {}
        if exists(self.path):
            try:
                with open(self.path, 'rb') as f:
                    R = pickle.load(f)
            except:
                print('load PersistentData from %s failed' % self.path)
                traceback.print_exc()
        
        self.USER_PLAYLISTS = R.get('USER_PLAYLISTS', {})
        self.VK_AUDIOS = R.get('VK_AUDIOS', {})
    
    def save(self):
        R = {
            'USER_PLAYLISTS':self.USER_PLAYLISTS,
            'VK_AUDIOS': self.VK_AUDIOS,
        }
        if exists(self.path):
            # dumps first to check if it's pickle'able
            pickle.dumps(R)

        with open(self.path, 'wb') as f:
            pickle.dump(R ,f)

    def get_path(self):
        return '__STORAGE.pickle'
    
PD = PersistentData()


#%%% 

if __name__=='__main__':
    print('This is ...')
    pass

#%%% 