#!/usr/bin/env python
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards.
"""
import json
import logging
import requests

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaAudio, InputFile
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

from vk_funcs import ep_vk_search, ep_vk_audio_by_ids

from auths import *

n_results_per_page = 10

SAVED  = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

CONTEXT = None
UPDATE = None

def shuffle_str(s):
    import random
    x = [c for c in s]
    random.shuffle(x)
    return ''.join(x)

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти')
    return
    keyboard = [
        [
            InlineKeyboardButton("Option 1", callback_data='1'),
            InlineKeyboardButton("Option 2", callback_data='2'),
        ],
        [InlineKeyboardButton("Option 3", callback_data='3')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    global UPDATE
    UPDATE = update
    global CONTEXT 
    CONTEXT = context
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    
    ids = query.data
    
    # r = ep_vk_audio_by_ids(ids)
    global SAVED
    
    if(ids not in SAVED):
        print(SAVED)
        print(ids)
        logging.getLogger().info('%s not in SAVED!' % ids)
        r = ep_vk_audio_by_ids(ids)
        SAVED[ids] = r
        # raise ValueError('WTF!???!')
    
    r = SAVED[ids]
    
    #query.message.reply_text(f"Selected option: {query.data}")
    # query.message.reply_text(json.dumps(r))
    # query.edit_message_text(text=f"Selected option: {query.data}")

    logging.getLogger().info('Getting %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))


    R = requests.get(r['url'])

    if r['track_covers']:
        thumb = requests.get(r['track_covers'][0]).content
    else:
        thumb = None
    
    query.message.reply_audio(
        R.content,
        duration=r['duration'],
        title=r['title'],
        performer=r['artist'],
        thumb=thumb
        )
    logging.getLogger().info('Got %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))


def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Use /start to test this bot.")

def time_str(dur):
    rs = ''
    was = 0
    for d in [3600,60,1]:
        if was:
            rs = rs+':%02i' % int(dur/d)
        else:
            if dur > d:
                rs = rs + '%i' % int(dur/d)
            
                was = 1
        dur = dur % d
            
    return rs

def prepare_keyboard(q, R, page):
    global SAVED
    
    # return [[InlineKeyboardButton('a', callback_data='a')]]
    keyboard = [
            [InlineKeyboardButton(
                r['artist']+' - '+r['title']+'  '+time_str(r['duration']),
                callback_data=r['callback_data']
            )]
            for j,r in enumerate(R)
        ]
    
    # if(page==0):
    #     if(len(R)<10):
    #         pass
    #     else:
    #         keyboard.append([InlineKeyboardButton(">", callback_data=json.dumps({'q':q,'page':page+1}))])
    # else:
    #     if(len(R)<10):
    #         keyboard.append([InlineKeyboardButton("<", callback_data=json.dumps({'q':q,'page':page-1}))])
    #     else:
    #         keyboard.append([
    #                 InlineKeyboardButton("<", callback_data=json.dumps({'q':q,'page':page-1})),
    #                 InlineKeyboardButton(">", callback_data=json.dumps({'q':q,'page':page+1}))
    #             ])    
    return keyboard

def message(update: Update, context: CallbackContext) -> None:
    s = update.message.text
    logging.getLogger().info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=n_results_per_page)
    logging.getLogger().info('Found : %i results' % len(R))
    
    if len(R)==0:
        logging.getLogger().info('nothing..')
        update.message.reply_text('Ничего не нашлось..')
    else:
        global SAVED
        for r in R:
            r['callback_data'] = str(r['owner_id'])+'|'+str(r['id'])
            SAVED[r['callback_data']] = {k:r[k] for k in r}
       
        keyboard = prepare_keyboard(s, R, 0)
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Вот что нашёл:', reply_markup=reply_markup)

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(AUTHS[2])

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, message))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()