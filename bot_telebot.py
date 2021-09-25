# -*- coding: utf-8 -*-
"""
Created on %(date)s

TODO: proper url-en/de-code

@author: %(username)s
"""


#%%% imports

import asyncio
import io
import logging
import telebot
import tempfile
import traceback
import urllib.parse

from time import sleep
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaAudio, Audio

from common import de_async
from persistence import PD
from vk_funcs import ep_vk_search, ep_vk_audio_by_ids, ep_vk_finish, download_audio, download_cover, renew_connection
from shazam_funcs import shazam_recognize
from auths import AUTHS

# %%

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

DEBUG = {'msgs':[]}

# %%

class Options:
    n_results_per_page = 6
    send_log_messages = False

# %%

callback_data_dict = {}

# bot = telebot.TeleBot(AUTHS[2])
bot = telebot.AsyncTeleBot(AUTHS[2])

CHAT_STATES = {}
def get_chat_state(chat_id):
    if chat_id not in CHAT_STATES:
        CHAT_STATES[chat_id] = None
    return CHAT_STATES[chat_id]

def set_chat_state(chat_id, state):
    CHAT_STATES[chat_id] = state
    

J = 0
# %%
def new_callback_id():
    global J
    while(1):
        J = J+1
        if str(J) not in callback_data_dict:
          return J
        
def save_callback_data(data):
    id = str(new_callback_id())
    callback_data_dict[id] = data
    return id

def btn(text, callback_data=None):
    if type(callback_data)==list:
        callback_data = '/'+callback_data[0]+'?'+str(save_callback_data(callback_data[1]))
    return InlineKeyboardButton(text, callback_data=callback_data)

def markup(btns, callback_data=None):
    if type(btns)==list:
        if all(type(btn)==InlineKeyboardButton for btn in btns):
            return markup([[btn] for btn in btns])
        else:
            return InlineKeyboardMarkup(btns)
    elif type(btns)==str:
        return markup(btn(btns, callback_data=callback_data))
    else:
        return markup([[btns]])

# %%

def encode_callback_data(com_name, data_dict=None):
    if com_name[0]=='/':
        r = com_name[1:]
    else:
        r = com_name
    if data_dict is not None:
        return '/'+r+'?'+save_callback_data(data_dict)
    else:
        return '/'+r

def parse_url_pars(s):
    parsed = urllib.parse.parse_qs(s)
    return {k:parsed[k][0] for k in parsed}
    r = {}
    for ts in s.split('&'):
        if len(ts)>3:
            a = ts.split('=')
            r[a[0]]=a[1]
    return r

def bot_run_command(src_message, command=None):
    # there's probably a function that does that correctly
    #  already in bot or in telebot.utils somewhere, but..
    com_name = command or src_message.text
    if com_name[0]=='/':
        com_name = com_name[1:]
    if com_name.find('?')>0:
        # Am I reinventing the internet with this?
        kwargs = callback_data_dict.get(com_name[com_name.find('?')+1:], {})
        com_name = com_name[:com_name.find('?')]
    else:
        kwargs = {}
    print('\nbot_run_command:\ncon_name=%s\nkwargs=%s\n..' % (com_name, str(kwargs)))
    for handler in bot.message_handlers:
        if 'commands' in handler['filters']\
            and com_name in  handler['filters']['commands']:
            print('running sth')
            return handler['function'](src_message, **kwargs)        

@bot.message_handler(commands=['start'])
def on_start(message):
    bot.send_message(
        message.chat.id, (
        'Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти\n'
        ' или записывай аудио-сообщение, распознаю'
        '\n\n'
        'Hi! send text to search audios or record to recognize'
        ),
        reply_markup=home_reply_markup(message.chat.id)
    )
    

@bot.message_handler(commands=['albums'])
def albums_fun(message):
    albums = PD.get_chat_albums(message.chat.id)
    print('\n\n%s\n\n' % list(albums.keys()))
    if len(albums)==0:
        bot.send_message(
            message.chat.id, 
            'no albums yet',
            reply_markup=markup('new album', callback_data='/new_album')
        )
    else:
        bot.send_message(
            message.chat.id, 
            'Albums:',
            reply_markup=markup([btn(album_name + '(%i)' % len(albums[album_name]), callback_data=['album',{'album_name':album_name}])
                for album_name in albums
            ] + [
                btn('new album', callback_data='/new_album')
            ])
        )

@bot.message_handler(commands=['album'])
def album_fun(message, album_name=None):
    print('album_fun')
    if album_name is None:
        return albums_fun(message)
    print(' album_name='+album_name)
    
    album = PD.get_album_or_add(message.chat.id, album_name)
    print(album)
    if len(album)==0:
        return home_fun(message, text='album is empty')
    else:
        bot.send_media_group(
            message.chat.id,
            [InputMediaAudio(file_id) for file_id in album],
            # reply_markup=home_reply_markup(message.chat.id)
        ).wait()
        
        home_fun(message, text='^ ^', add_btns=[btn('Delete album', callback_data=['delete_album',{'album_name':album_name}])])
        
@bot.message_handler(commands=['delete_album'])
def delete_album_fun(message, album_name=None):
    if album_name is None:
        return home_fun(message, text='error..')
    PD.delete_chat_album(message.chat.id, album_name)
    home_fun(message, text='album %s deleted' % album_name)
        

def home_reply_markup(chat_id, add_btns=None):
    if add_btns is None:
        add_btns = []
    return markup(add_btns + [
            btn('new album', callback_data='/new_album')
            if not PD.have_albums(chat_id)
            else btn('albums', callback_data='/albums')
            , btn( 'renew vk conn..', callback_data='/renew')
        ])

@bot.message_handler(commands=['go_home'])
def home_fun(message, text=None, add_btns=None):
    if text is None:
        text = 'Send text to search for music, send voice to recognize' 
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=home_reply_markup(message.chat.id, add_btns=add_btns)
    )

@bot.message_handler(commands=['add_ids_to_album_init'])
def add_ids_to_album_init_fun(message, ids=None, album_name=None):
    if ids is None:
        return home_fun(message, text='error..')
    print('add_ids_to_album_init_fun ids=%s' % ids)
    albums = PD.get_chat_albums(message.chat.id)
    print('\n\n%s\n\n' % list(albums.keys()))
    if len(albums)==0:
        bot.send_message(
            message.chat.id, 
            'no albums yet',
            reply_markup=home_reply_markup(message.chat.id)
        )
    # elif len(albums)==1:
    #     # We know what we're doing!
    #     add_ids_to_album_for_fun(message, ids=ids, album_name=list(albums.keys())[0])
    else:
        print([album_name + ('(%i)' % len(albums[album_name]))
                for album_name in albums])
        print(['/add_ids_to_album?ids='+ids+'&album_name='+album_name
                for album_name in albums])
        DEBUG['markup'] = markup([
                btn(album_name + ('(%i)' % len(albums[album_name]))
                    ,callback_data=encode_callback_data('/add_ids_to_album',{'ids':ids, 'album_name':album_name}))
                for album_name in albums
            ] + [
                btn('new album', callback_data='/new_album')
            ])
        DEBUG['task'] = bot.send_message(
            message.chat.id, 
            'Add where?',
            reply_markup=markup([
                btn(album_name + ('(%i)' % len(albums[album_name]))
                    ,callback_data=encode_callback_data('/add_ids_to_album',{'ids':ids, 'album_name':album_name}))
                for album_name in albums
            ] + [
                btn('new album', callback_data='/new_album')
            ])
        )
    pass

@bot.message_handler(commands=['add_ids_to_album'])
def add_ids_to_album_for_fun(message, ids=None, album_name=None):
    if album_name is None or ids is None:
        home_fun(message, text='some error..')
    file_id = PD.get_ids_file_id(ids)
    
    album = PD.get_album_or_add(message.chat.id, album_name)
    if file_id not in album:
        album.append(file_id)
        print('added to %s , now there are %i' % (album_name, len(album)))
    else:
        print('already there')
    album_fun(message, album_name=album_name)
    
            
class CONSTS:
    NEW_ALBUM = 'new album'
    ADD_TO_NEW_ALBUM = 'add to new album'

@bot.message_handler(commands=['new_album'])
def new_album_fun(message):
    msg = bot.reply_to(
        message,
        'Enter new album name:',
        reply_markup=markup('Cancel', callback_data='/go_home')
    ).wait()
    set_chat_state(message.chat.id, CONSTS.NEW_ALBUM)

def new_album_name_fun(message):
    new_name = message.text
    print('\n\n new album name: %s' % new_name)
    if PD.have_album(message.chat.id, new_name):
        msg = bot.reply_to(
            message,
            'Taken. Enter new album name:',
            reply_markup=markup('Cancel', callback_data='/go_home')
        ).wait()
        set_chat_state(message.chat.id, CONSTS.NEW_ALBUM)
    else:
        PD.get_album_or_add(message.chat.id, new_name)
        msg = bot.reply_to(
            message,
            'Album *%s* created' % new_name,
            reply_markup=home_reply_markup(message.chat.id)
        )
        set_chat_state(message.chat.id, None)

@bot.message_handler(commands=['all'])
def send_all(message):
    group = []
    for k in PD.VK_AUDIOS :
        if 'telegram' in PD.VK_AUDIOS[k]\
            and 'chat_ids' in PD.VK_AUDIOS[k]\
            and message.chat.id in PD.VK_AUDIOS[k]['chat_ids']:
            print(PD.VK_AUDIOS[k])
            group.append(InputMediaAudio(
                PD.VK_AUDIOS[k]['telegram']['file_id']
            ))      
        else:
            print('..no telegram data..')
    
    if len(group)>0:
        DEBUG['send_all_task'] = bot.send_media_group(message.chat.id, group)
    else:
        bot.send_message(
            message.chat.id, (
            'no audios yet'
            )
        )        
    
@bot.message_handler(commands=['renew'])
def on_renew(message):
    try:
        renew_connection()
        bot.send_message(
            message.chat.id, (
            'VK conection renewed'
            )
        )
    except:
        traceback.print_exc()
        try:
            bot.send_message(
                message.chat.id, (
                'some error..'
                )
            )
        except:
            pass
    
# Handles all sent documents and audio files
@bot.message_handler(content_types=['voice', 'audio'])
def handle_docs_audio(message):
    print(message)
    DEBUG['msgs'].append(message)
    
    file_id = (message.voice if message.voice is not None else message.audio).file_id
    
    print('getting file..')
    file = bot.get_file(file_id).wait()
    
    print('downloading file..')
    content = bot.download_file(file.file_path).wait()
    
    print('recognizing file..')
    rec = shazam_recognize(content)
    
    print(rec)
    DEBUG['rec'] = rec
    
    if len(rec['matches'])==0:
        bot.reply_to(message, 'Nothing found, sorry..')     
   
    else:
        page_search(
            rec['track']['title']+' - '+rec['track']['subtitle'],
            message
        )
   
# @bot.message_handler(func=lambda message: True)
@bot.message_handler(content_types=['text'])
def message_handler(message):
    if message.text[0]=='/':
        bot_run_command(message, message.text)
    if get_chat_state(message.chat.id) == CONSTS.NEW_ALBUM:
        # register_next_step_handler is weird
        new_album_name_fun(message)
    else:
        set_chat_state(message.chat.id, None)
        page_search(message.text, message)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(query):
    set_chat_state(query.message.chat.id, None)
    global DEBUG
    DEBUG['query'] = query
    
    print(' \nQUERY:\n')
    print(query)
    print('')
    
    if(is_page_change_query(query)):
        # bot.answer_callback_query(query.id, "Листаю страницу..")
        
        r = PageCallbackData.parse(query.data)
        
        logger.info('looking at page %i for %s'
                                 % (r['page'],r['q']))

        page_search(r['q'], query.message, page=int(r['page']), edit=True)
    elif(query.data[0]=='/'):
        return bot_run_command(query.message, query.data)
    else:
        ids = query.data
        
        chat_id = query.message.chat.id
        
        handle_vk_audio_by_ids(chat_id, ids)

# %% Pages
      
def page_search(s, message, page=0, edit=False):
    bot.send_chat_action(message.chat.id, "typing")
    global DEBUG
    DEBUG['message'] = message
    logger.info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=Options.n_results_per_page, page=page)
    logger.info('Found : %i results' % len(R))
    
    if len(R)==0:
        logger.info('nothing..')
        bot.send_chat_action(message.chat.id)
        bot.reply_to(message, 'Ничего не нашлось..')
    else:
        reply_markup = prepare_keyboard(s, R, page)

        if edit:
            edit_message_reply_markup(message, reply_markup)
        else:
            bot.reply_to(message, 'Вот что нашёл:', reply_markup=reply_markup)


def prepare_keyboard(q, R, page):
    keyboard = [
            [btn(
                r['title_str'],
                callback_data=r['callback_data']
            )]
            for j,r in enumerate(R)
        ]
    
    prev_page_btn = page_button(q, page, -1)
    next_page_btn = page_button(q, page, 1)
    
    page_btns = []
    if page > 0:
        page_btns.append(prev_page_btn)
    if len(R) >= Options.n_results_per_page:
        page_btns.append(next_page_btn)
    
    if len(page_btns)>0:
        keyboard.append(page_btns)
    
    keyboard.append([btn('Home', callback_data='/go_home')])
    
    return markup(keyboard)


def edit_message_reply_markup(message, new_reply_markup):
    return bot.edit_message_reply_markup(
        chat_id=message.chat.id, 
        message_id=message.id,
        reply_markup=new_reply_markup
    )

def page_button(q, page, delta_n):
    return btn(
        "<" if delta_n < 0 else ">", 
        callback_data=PageCallbackData.gen(q, page + delta_n)
    )


class PageCallbackData:
    def is_one(s):
        return type(s)==str and len(s)>0 and s[0]=='{'

    def gen(q, page):
        return '{'+q+'|'+str(page)

    def parse(s):
        r = s[1:].split('|')
        return { 'q': r[0], 'page': int(r[1]) }
        
def is_page_change_query(query):
    return PageCallbackData.is_one(query.data)

# %% Audios

def handle_vk_audio_by_ids(chat_id, ids):
    init_log_msg(chat_id)
    # bot.answer_callback_query(query.id, "думаю..")
    
    if ids in PD.VK_AUDIOS:
        print('vk info cached')
        r = PD.VK_AUDIOS[ids]
        if chat_id not in r['chat_ids']:
            r['chat_ids'].append(chat_id)
    else:
        r = ep_vk_audio_by_ids(ids)
        
        r['chat_ids'] = [chat_id]
        PD.VK_AUDIOS[ids] = r
    print(r)
    
    DEBUG['r'] = r
    
    logger.info('Getting %s : %s' % (ids, r['title_str']))
    
    # first_msg = bot.send_audio(chat_id,
    #                 r['url'],
    #                 title=r['title'],
    #                 performer=r['artist'],
    #             )    
    try:
        reply_markup = markup((
        [
            btn('Add to album',['add_ids_to_album_init',{'ids':ids}])
        ] if PD.have_albums(chat_id) else []) +[
            btn('Home','/go_home')
        ])
        if 'telegram' in r:
            print('telegram info cached')
            media = r['telegram']['file_id']
            task = bot.send_audio(chat_id, media, reply_markup=reply_markup)
        else:
            bot.send_chat_action(chat_id, "record_voice")
            
            content = download_audio(r['url'], log_msg)
        
            thumb = None
            if r['track_covers']:
                thumb = download_cover(r['track_covers'], log_msg)
            else:
                thumb = None
            
            task = bot.send_audio(chat_id,
                content,
                duration=r['duration'],
                title=r['title'],
                performer=r['artist'],
                thumb=thumb,
                reply_markup=reply_markup,
            )
        
        # bot.answer_callback_query(query.id, "отправляю..")
        log_msg('отправляю..')

        bot.send_chat_action(chat_id, "upload_document")
        
        # task = bot.send_media_group(chat_id, [media,media,media])

        DEBUG['task'] = task
        
        
        
        # # -- doesnt work =(
        # bot.edit_message_media(
        #     InputMediaAudio(
        #         content,
        #         duration=r['duration'],
        #         title=r['title'],
        #         performer=r['artist'],
        #         thumb=thumb,
        #     ),
        #     chat_id=chat_id,
        #     message_id=first_msg.id,
        # )
        
        while not task.done:
            bot.send_chat_action(chat_id, "upload_document")
            sleep(.1)
        
        logger.info('Got %s : %s' % (ids, r['title_str']))
        
        if 'telegram_file_id' not in r:
            print('logging new telegram_file_id')
        r['telegram'] = {
            'file_id': task.result.audio.file_id,
            'file_unique_id': task.result.audio.file_unique_id,
        }
        print(r['telegram']['file_id'])
    
        delete_log_msg()
    except:
        log_msg('ошибка')
        logger.warning(str(r))
        logger.warning(traceback.format_exc())
        # send_exc(query.message, traceback.format_exc())
    
        try:
            bot.send_audio(chat_id,
                    r['url'],
                    title=r['title'],
                    performer=r['artist'],
                )
        except:
            traceback.print_exc()

_log_msg = None
def init_log_msg(chat_id):
    global _log_msg
    if Options.send_log_messages:
        _log_msg = bot.send_message(chat_id, "думаю..").wait()
    
def log_msg(s):
    logger.info(s)
    global _log_msg
    if Options.send_log_messages and (_log_msg is not None):
        _log_msg.text = _log_msg.text + s
        bot.edit_message_text(
            _log_msg.text, 
            chat_id = _log_msg.chat.id, 
            message_id=_log_msg.id
        )

def delete_log_msg():
    global _log_msg
    if Options.send_log_messages and (_log_msg is not None):
        bot.delete_message(chat_id=_log_msg.chat.id, message_id=_log_msg.id)
    _log_msg = None

#%%% default listener to log everything to output

def listener(messages):
    for m in messages:
        print(str(m))

#%%% 

def main():
    bot.set_update_listener(listener)
    
    me = bot.get_me().wait()
    
    print('I am:\n%s\nSecurity token:\n%s' % (
        {s:me.__dict__[s] for s in ['id', 'first_name', 'username']}
        ,AUTHS[2]
    ))
        
        
    print('listening..')
    try:
        bot.polling()
    except KeyboardInterrupt:
        print('Ctrl-C..')
    finally:
        PD.save()
    
    
    pass

#%%% 

if __name__=='__main__':
    print('This is ep_vk_music_telebot')
 
    main()

