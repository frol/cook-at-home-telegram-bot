import pathlib

import telebot

from . import common

TELEGRAM_TOKEN = None
ADMIN_CHAT_ID = None

CATEGORIES = {
    "Необычное": ["Хуммус", "Вареники с картохой"],
    "Easy": ["Паста с сыром"],
}

DISHES_OF_THE_WEEK = ["Хуммус"]

DISHES_FOLDER = pathlib.Path("./dishes")

from .local_config import *


telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(TELEGRAM_TOKEN)


from .dish import load_dishes

DISHES = {dish.name: dish for dish in load_dishes(DISHES_FOLDER)}


MENU = {
    dish_category: [DISHES[dish_name] for dish_name in dish_names]
    for dish_category, dish_names in CATEGORIES.items()
}
MENU_OF_THE_WEEK = [DISHES[dish_name] for dish_name in DISHES_OF_THE_WEEK]

MENU_KEYBOARD = telebot.types.ReplyKeyboardMarkup()
MENU_KEYBOARD.row_width = 2
MENU_KEYBOARD.add(
    *[telebot.types.KeyboardButton(menu_type) for menu_type in MENU.keys()]
)
MENU_KEYBOARD.row(telebot.types.KeyboardButton(common.KEYBOARD_BACK))
