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
    USER_DATA = {}
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
    
    def get_chat_albums(self, chat_id):
        if chat_id not in self.USER_PLAYLISTS:
            self.USER_PLAYLISTS[chat_id] = {'Первый альбом':[]}
        return self.USER_PLAYLISTS[chat_id]
        
    def have_ids(self, ids):
        return ids in self.VK_AUDIOS
    
    def get_ids_file_id(self, ids):
        return self.VK_AUDIOS[ids]['telegram']['file_id']
    
    def get_album_or_add(self, chat_id, album_name):
        albums = self.get_chat_albums(chat_id)
        if album_name not in albums:
            albums[album_name] = []
        return albums[album_name]
        
    def have_albums(self, chat_id):
        return len(self.get_chat_albums(chat_id))>0
    
    def have_album(self, chat_id, album_name):
        return album_name in self.get_chat_albums(chat_id)
    
    def delete_chat_album(self, chat_id, album_name):
        albums = self.get_chat_albums(chat_id)
        if album_name in albums:
            del albums[album_name]
    
    def add_to_album(self, chat_id, album_name, file_id):
        album = self.get_album_or_add(chat_id, album_name)
        if file_id not in album:
            album.append(file_id)

    
PD = PersistentData()


#%%% 

if __name__=='__main__':
    print('This is ...')
    pass

#%%% 
