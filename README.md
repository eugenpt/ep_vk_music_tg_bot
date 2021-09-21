# ep vk music tg bot

Telegram Bot to search and download music from [VK](https://vk.com)
 
(proven (by me and for me) to be more reliable for offline than official VK music app (BOOM?). also this one is free)

my own version is sometimes available at [@ep_vk_music_bot](https://t.me/ep_vk_music_bot)

(it speaks Russian but it's pretty straightforward)

## installation

First, create a bot using [@BotFather](https://t.me/BotFather)
( `/start` -> `/newbot` -> `<follow instruction>` )

Then clone the repo, inside it create a file `__auths.txt` and fill it with:
```
<VK.com login>
<VK.com password>
<telegram bot token received from @BotFather>
```
(Archaic and not really user-friendly. I know. This is the way.)

then simply install requirements:
```
pip install -r requirements.txt
```
And then run the thing
```
python bot.py
```
( use *env/... if you know what it is. and want to )



