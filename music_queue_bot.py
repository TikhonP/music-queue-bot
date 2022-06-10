#!/usr/bin/env python

"""
Bot for storing music albums and releases to the queue
"""
import json
import logging
import os
from pathlib import Path

import requests
import sentry_sdk
import validators
from telegram import Update, ParseMode
from telegram.ext import CallbackContext, CommandHandler, Updater, MessageHandler, Filters

sentry_sdk.init(
    "https://adf592c337cb4811824d5a7eed09297f@o1075119.ingest.sentry.io/6486828",

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0
)

TOKEN = os.environ.get('MUSIC_QUEUE_TELEGRAM_TOKEN')
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILENAME = os.path.join(BASE_DIR, 'music_queue_bot', 'music_queue_bot.json')
DATA = {}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def get_song_links(url: str):
    answer = requests.get("https://api.song.link/v1-alpha.1/links", params={
        'url': url,
        'userCountry': 'RU'
    }).json()
    song_data = answer['entitiesByUniqueId'][next(iter(answer['entitiesByUniqueId']))]
    out_text = f'{song_data["artistName"]} - {song_data["title"]}\n'
    reply_urls = []
    for platform, link in answer['linksByPlatform'].items():
        reply_urls.append(f'<a href="{link["url"]}">{platform}</a>')
    out_text += ' | '.join(reply_urls)
    return out_text


def get_data(filename: str) -> dict:
    """Reads data from json file and returns dict"""

    try:
        with open(filename) as f:
            return json.load(f)
    except FileNotFoundError:
        store_data({}, filename)
        return {}


def store_data(data: dict, filename: str):
    """Stores python object serialized to json data to file"""

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(data, f)


def start(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /start is issued."""

    user = update.effective_user
    if str(user.id) not in DATA:
        DATA[str(user.id)] = []
        store_data(DATA, CONFIG_FILENAME)
    logger.info("User %s connected.", user.first_name)
    update.message.reply_text(
        f'Привет {user.full_name}! Чтобы добавить объект в очередь просто кинь ссылку, '
        'чтобы взять что-то нажми /get'
    )


def help_command(update: Update, _: CallbackContext) -> None:
    """Send a message when the command /help is issued."""

    update.message.reply_text(
        'Чтобы добавить объект в очередь просто кинь ссылку, '
        'чтобы взять что-то нажми /get'
    )


def receive_message(update: Update, _: CallbackContext) -> None:
    """When receive message if message is web link add it to the queue"""

    if not validators.url(update.message.text):
        update.message.reply_text('Это не ссылка.')
    else:
        user = update.effective_user
        DATA[str(user.id)].append(update.message.text)
        store_data(DATA, CONFIG_FILENAME)
        update.message.reply_text('Добавил.')


def get_object_from_queue(update: Update, _: CallbackContext) -> None:
    """Command for get object from user queue"""

    user = update.effective_user
    if DATA[str(user.id)]:
        update.message.reply_text(
            get_song_links(DATA[str(user.id)].pop(0)),
            parse_mode=ParseMode.HTML
        )
        store_data(DATA, CONFIG_FILENAME)
    else:
        update.message.reply_text('Очередь пуста.')


def main() -> None:
    """Start the bot."""

    global DATA

    if TOKEN is None:
        logger.error("None token exported")
        exit()

    DATA = get_data(CONFIG_FILENAME)
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('get', get_object_from_queue))

    message = MessageHandler(Filters.text & (~Filters.command), receive_message)
    dispatcher.add_handler(message)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
