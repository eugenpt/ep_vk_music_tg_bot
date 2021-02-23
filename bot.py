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

from vk_funcs import ep_vk_search, ep_vk_audio_by_ids, ep_vk_finish

from auths import *

n_results_per_page = 10

SAVED  = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


global DEBUG
DEBUG = {}


def shuffle_str(s):
    import random
    x = [c for c in s]
    random.shuffle(x)
    return ''.join(x)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти')


def button(update: Update, context: CallbackContext) -> None:
    global DEBUG
    DEBUG['context'] = context
    DEBUG['update'] = update

    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    
    ids = query.data
    
    if(ids[0]=='{'):
        # page stuff!
        logging.getLogger().debug('json? %s' % ids)
        r = json.loads(ids)
        logging.getLogger().debug('json! %s' % json.dumps(r))
        
        logging.getLogger().info('looking at page %i for %s'
                                 % (r['page'],r['q']))
        
        page_search(r['q'], query.message, page=int(r['page']), edit=True)
    else:
        # r = ep_vk_audio_by_ids(ids)
        global SAVED
        
        if(ids not in SAVED):
            logging.getLogger().info('%s not in SAVED! getting from vk..' % ids)
            r = ep_vk_audio_by_ids(ids)
            SAVED[ids] = r
        
        r = SAVED[ids]
        
        msg = query.message.reply_text("думаю..")
        DEBUG['msg'] = msg
        
        logging.getLogger().info('Getting %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))
    
        try:
            R = requests.get(r['url'])
        
            if r['track_covers']:
                thumb = requests.get(r['track_covers'][0]).content
            else:
                thumb = None
            
            # msg.edit_media(InputMediaAudio(
            query.message.reply_audio(
                R.content,
                duration=r['duration'],
                title=r['title'],
                performer=r['artist'],
                thumb=thumb
                )
            msg.delete()
            # InputMediaAudio()
            
            logging.getLogger().info('Got %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))
        except Exception as e:
            msg.edit_text('Error! %s' % str(e))
            pass
        

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
    
    keyboard = [
            [InlineKeyboardButton(
                r['artist']+' - '+r['title']+'  '+time_str(r['duration']),
                callback_data=r['callback_data']
            )]
            for j,r in enumerate(R)
        ]
    
    # page movers
    if(page==0):
        if(len(R)<10):
            pass
        else:
            keyboard.append([InlineKeyboardButton(">", callback_data=json.dumps({'q':q,'page':page+1}))])
    else:
        if(len(R)<10):
            keyboard.append([InlineKeyboardButton("<", callback_data=json.dumps({'q':q,'page':page-1}))])
        else:
            keyboard.append([
                    InlineKeyboardButton("<", callback_data=json.dumps({'q':q,'page':page-1})),
                    InlineKeyboardButton(">", callback_data=json.dumps({'q':q,'page':page+1}))
                ])    
    return keyboard



def message(update: Update, context: CallbackContext) -> None:
    page_search(update.message.text, update.message)

def page_search(s, message, page=0, edit=False):
    logging.getLogger().info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=n_results_per_page, page=page)
    logging.getLogger().info('Found : %i results' % len(R))
    
    if len(R)==0:
        logging.getLogger().info('nothing..')
        message.reply_text('Ничего не нашлось..')
    else:
        global SAVED
        for r in R:
            r['callback_data'] = str(r['owner_id'])+'|'+str(r['id'])
            SAVED[r['callback_data']] = {k:r[k] for k in r}
       
        keyboard = prepare_keyboard(s, R, page)
        reply_markup = InlineKeyboardMarkup(keyboard)
        if edit:
            message.edit_reply_markup(reply_markup)
        else:
            message.reply_text('Вот что нашёл:', reply_markup=reply_markup)
            

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
    
    ep_vk_finish()


if __name__ == '__main__':
    main()