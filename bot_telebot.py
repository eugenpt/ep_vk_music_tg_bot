# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s
"""


#%%% imports

import asyncio
import io
import logging
import telebot
import tempfile
import traceback

from time import sleep
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from common import de_async
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

# bot = telebot.TeleBot(AUTHS[2])
bot = telebot.AsyncTeleBot(AUTHS[2])


# %%

@bot.message_handler(commands=['start'])
def on_start(message):
    bot.send_message(
        message.chat.id, (
        'Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти'
        ' или записывай аудио-сообщение, распознаю'
        '\n'
        'Hi! send text to search audios or record to recognize'
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
    page_search(message.text, message)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(query):
    global DEBUG
    DEBUG['query'] = query
    
    if(is_page_change_query(query)):
        # bot.answer_callback_query(query.id, "Листаю страницу..")
        
        r = PageCallbackData.parse(query.data)
        
        logger.info('looking at page %i for %s'
                                 % (r['page'],r['q']))

        page_search(r['q'], query.message, page=int(r['page']), edit=True)
    else:
        ids = query.data
        
        chat_id = query.message.chat.id
        
        handle_vk_audio_by_ids(chat_id, ids)

# %% Pages
      
def page_search(s, message, page=0, edit=False):
    bot.send_chat_action("typing")
    global DEBUG
    DEBUG['message'] = message
    logger.info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=Options.n_results_per_page, page=page)
    logger.info('Found : %i results' % len(R))
    
    if len(R)==0:
        logger.info('nothing..')
        bot.reply_to(message, 'Ничего не нашлось..')
    else:
        reply_markup = prepare_keyboard(s, R, page)

        if edit:
            edit_message_reply_markup(message, reply_markup)
        else:
            bot.reply_to(message, 'Вот что нашёл:', reply_markup=reply_markup)


def prepare_keyboard(q, R, page):
    keyboard = [
            [InlineKeyboardButton(
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
    
    return InlineKeyboardMarkup(keyboard)


def edit_message_reply_markup(message, new_reply_markup):
    return bot.edit_message_reply_markup(
        chat_id=message.chat.id, 
        message_id=message.id,
        reply_markup=new_reply_markup
    )

def page_button(q, page, delta_n):
    return InlineKeyboardButton(
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
    
    r = ep_vk_audio_by_ids(ids)
    print(r)
    
    DEBUG['r'] = r
    
    logger.info('Getting %s : %s' % (ids, r['title_str']))
    
    # first_msg = bot.send_audio(chat_id,
    #                 r['url'],
    #                 title=r['title'],
    #                 performer=r['artist'],
    #             )    
    try:
        bot.send_chat_action(chat_id, "record_voice")
        
        content = download_audio(r['url'], log_msg)
    
        thumb = None
        if r['track_covers']:
            thumb = download_cover(r['track_covers'], log_msg)
        else:
            thumb = None
        
        # bot.answer_callback_query(query.id, "отправляю..")
        log_msg('отправляю..')
        
        # first_msg = first_msg.wait()
        bot.send_chat_action(chat_id, "upload_document")
    
        task = bot.send_audio(chat_id,
            content,
            duration=r['duration'],
            title=r['title'],
            performer=r['artist'],
            thumb=thumb,
        )
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

if __name__=='__main__':
    print('This is ep_vk_music_telebot')
    
    bot.set_update_listener(listener)
    
    me = bot.get_me().wait()
    
    print('I am:\n%s\nSecurity token:\n%s' % (
        {s:me.__dict__[s] for s in ['id', 'first_name', 'username']}
        ,AUTHS[2]
    ))
    
    print('listening..')
    bot.polling()
    
    pass

#%%% 
