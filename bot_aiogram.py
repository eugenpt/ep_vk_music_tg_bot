

import asyncio
import logging

from aiogram import Bot, Dispatcher, executor, filters, types
from logging.handlers import RotatingFileHandler

import ep_log
from auths import AUTHS
from common import de_async

## %%

logger = logging.getLogger("ep." + __name__)
DEBUG = {'msgs':[]}

API_TOKEN = AUTHS[2]


class EP_TG_BOT(Bot):
    USER_DATA = {}
    USER_PLAYLISTS = {}  # per user
    VK_AUDIOS = {}  # including telegram file_ids (!)

    def __init__(self, _path=None):
        self.path = _path or self.get_path()
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
            'USER_PLAYLISTS': self.USER_PLAYLISTS,
            'VK_AUDIOS': self.VK_AUDIOS,
        }
        if exists(self.path):
            # dumps first to check if it's pickle'able
            pickle.dumps(R)

        with open(self.path, 'wb') as f:
            pickle.dump(R, f)

    def get_path(self):
        return '__STORAGE.pickle'

    def get_chat_albums(self, chat_id):
        if chat_id not in self.USER_PLAYLISTS:
            self.USER_PLAYLISTS[chat_id] = {'Первый альбом': []}
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
        return len(self.get_chat_albums(chat_id)) > 0

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

    pass
    def btn(self, ):


bot = EP_VK_TG(token=API_TOKEN)
bot_user = de_async(bot.get_me())
logger.info(
    f'Me: {bot_user.username} '
    f'Token: {bot._token}'
)

dp = Dispatcher(bot)


@dp.message_handler(commands='start')
async def send_welcome(message: types.Message):
    # So... At first I want to send something like this:
    await message.reply(
        'Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти\n'
        ' или записывай аудио-сообщение, распознаю'
        '\n\n'
        'Hi! send text to search audios or record to recognize'
    )

    # Wait a little...
    await asyncio.sleep(1)

    # Good bots should send chat actions...
    await types.ChatActions.upload_photo()

    # Create media group
    media = types.MediaGroup()

    # Attach local file
    media.attach_photo(types.InputFile('data/cat.jpg'), 'Cat!')
    # More local files and more cats!
    media.attach_photo(types.InputFile('data/cats.jpg'), 'More cats!')

    # You can also use URL's
    # For example: get random puss:
    media.attach_photo('http://lorempixel.com/400/200/cats/', 'Random cat.')

    # And you can also use file ID:
    # media.attach_photo('<file_id>', 'cat-cat-cat.')

    # Done! Send media group
    await message.reply_media_group(media=media)


def home_reply_markup(chat_id, add_btns=None):
    if add_btns is None:
        add_btns = []
    return markup(add_btns + [
            btn('new album', callback_data='/new_album')
            if not PD.have_albums(chat_id)
            else btn('albums', callback_data='/albums')
            , btn( 'renew vk conn..', callback_data='/renew')
        ])

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

# %%