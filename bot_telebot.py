# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s
"""


#%%% imports

import logging
import telebot
import traceback

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaAudio

from vk_funcs import ep_vk_search, ep_vk_audio_by_ids, ep_vk_finish, download_audio, download_cover
from auths import AUTHS

# %%

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

DEBUG = {}

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
        message.chat.id, 
        'Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти'
    )

   
@bot.message_handler(func=lambda message: True)
def message_handler(message):
    page_search(message.text, message)


def page_search(s, message, page=0, edit=False):
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


            
#%%%
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

# %%

def page_button(q, page, delta_n):
    return InlineKeyboardButton(
        "<" if delta_n < 0 else ">", 
        callback_data=PageCallbackData.gen(q, page + delta_n)
    )

# %%

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



# %%

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

        init_log_msg(chat_id)
        # bot.answer_callback_query(query.id, "думаю..")

        r = ep_vk_audio_by_ids(ids)
        print(r)

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

            bot.send_audio(chat_id,
                content,
                duration=r['duration'],
                title=r['title'],
                performer=r['artist'],
                thumb=thumb,
            )
            
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
#%%% 

def listener(messages):
    for m in messages:
        print(str(m))

#%%% 

if __name__=='__main__':
    print('This is ep_vk_music_telebot')
    
    bot.set_update_listener(listener)
    bot.polling()
    
    pass

#%%% 