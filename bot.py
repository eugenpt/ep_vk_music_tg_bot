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
import socket
import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaAudio, InputFile
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

from vk_funcs import ep_vk_search, ep_vk_audio_by_ids, ep_vk_finish, vk_audio_id_encode, download_audio

from auths import *

socket._GLOBAL_DEFAULT_TIMEOUT = 100

n_results_per_page = 10
n_results_per_page = 6

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

def log(*args):
    logger.info(*args)

def info(*args):
    logger.info(*args)

def debug(*args):
    logger.debug(*args)

def warning(*args):
    logger.warning(*args)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Здравствуй! Ищу и качаю музыку с вконтакте, пиши что надо найти')

MAX_MESSAGE_LEN = 500
def send_exc(message, s, print_also=True):
    if print_also:
        print(s)

    try:
        message.reply_text(s[:MAX_MESSAGE_LEN])
        if len(s)>MAX_MESSAGE_LEN:
            send_exc(message,s[MAX_MESSAGE_LEN:], print_also=False)
    except:
        traceback.print_exc()

def msg_add_text(msg, s):
    msg.text = msg.text + s
    msg.edit_text(msg.text)

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
        # debug('json? %s' % ids)
        # r = json.loads(ids)
        # debug('json! %s' % json.dumps(r))
        
        ts = ids[1:].split('|')
        
        r = {'q':ts[0], 'page':int(ts[1])}
        
        info('looking at page %i for %s'
                                 % (r['page'],r['q']))
        
        page_search(r['q'], query.message, page=int(r['page']), edit=True)
    else:
        # r = ep_vk_audio_by_ids(ids)
        global SAVED
        
        if(ids not in SAVED):
            info('%s not in SAVED! getting from vk..' % ids)
            r = ep_vk_audio_by_ids(ids)
            SAVED[ids] = r
        
        r = SAVED[ids]
        
        msg = query.message.reply_text("думаю..")
        DEBUG['msg'] = msg
        
        info('Getting %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))
        
        print(r)
    
        try:
            msg_add_text(msg, 'скачиваю аудио..')
            
            content = download_audio(r['url'])

            log('audio downloaded, ~%.1f MB' % (len(content)/(1024*1024)))
        
            thumb = None
            if r['track_covers']:
                msg_add_text(msg, 'обложки..')
                log('loading cover..')
                
                exc_str = None
                for track_url in r['track_covers']:
                    try:
                        thumb = requests.get(track_url, timeout=10).content
                        log('ok')
                        msg_add_text(msg, 'ок..')
                        break
                    except:
                        exc_str = traceback.format_exc()
                        pass
                        # send_exc(query.message, traceback.format_exc())
                if thumb is None:
                    log('could not load cover')
                    msg_add_text(msg, 'ошибка..')
                    log(exc_str)
                    send_exc(query.message, exc_str)
            else:
                thumb = None
            
            msg_add_text(msg, 'отправляю..')
            # msg.edit_media(InputMediaAudio(
            query.message.reply_audio(
                content,
                duration=r['duration'],
                title=r['title'],
                performer=r['artist'],
                thumb=thumb,
                )
            msg.delete()
            # InputMediaAudio()
            
            info('Got %s : %s' % (ids, r['artist']+' - '+r['title']+'  '+time_str(r['duration'])))
        except Exception as e:
            warning(str(r))
            warning(traceback.format_exc())
            # send_exc(query.message, traceback.format_exc())

            try:
                query.message.reply_audio(
                        r['url'],
                        title=r['title'],
                        performer=r['artist'],
                    )
            except:
                traceback.print_exc()
                pass
        

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
        if(len(R) < n_results_per_page):
            pass
        else:
            keyboard.append([InlineKeyboardButton(">", callback_data='{'+q+'|'+str(page+1))])#json.dumps({'q':q,'page':page+1}))])
    else:
        if(len(R) < n_results_per_page):
            keyboard.append([InlineKeyboardButton("<", callback_data='{'+q+'|'+str(page-1))])#json.dumps({'q':q,'page':page-1}))])
        else:
            keyboard.append([
                    InlineKeyboardButton("<", callback_data='{'+q+'|'+str(page-1)),#json.dumps({'q':q,'page':page-1})),
                    InlineKeyboardButton(">", callback_data='{'+q+'|'+str(page+1))#json.dumps({'q':q,'page':page+1}))
                ])    
    return keyboard



def message(update: Update, context: CallbackContext) -> None:
    page_search(update.message.text, update.message)

def page_search(s, message, page=0, edit=False):
    info('Looking for ' + s)
    
    R = ep_vk_search(s, n_results_per_page=n_results_per_page, page=page)
    info('Found : %i results' % len(R))
    
    if len(R)==0:
        info('nothing..')
        message.reply_text('Ничего не нашлось..')
    else:
        global SAVED
        for r in R:
            r['callback_data'] = vk_audio_id_encode(r['owner_id'],str(r['id']))
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