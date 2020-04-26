import telebot

from . import config
from .config import bot

START_KEYBOARD_MENU = "Меню"
START_KEYBOARD_DISHES_OF_THE_WEEK = "Набор недели"
START_KEYBOARD_CART = "Корзина"
START_KEYBOARD_HELP = "Инструкция"

START_KEYBOARD = telebot.types.ReplyKeyboardMarkup()
START_KEYBOARD.row(
    telebot.types.KeyboardButton(START_KEYBOARD_MENU),
    telebot.types.KeyboardButton(START_KEYBOARD_DISHES_OF_THE_WEEK),
    telebot.types.KeyboardButton(START_KEYBOARD_HELP),
)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Приступим", reply_markup=START_KEYBOARD)
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_start)


def handle_start(message):
    from .cart import send_cart
    from .menu import handle_menu

    if message.text == START_KEYBOARD_MENU:
        bot.send_message(
            message.chat.id, START_KEYBOARD_MENU, reply_markup=config.MENU_KEYBOARD
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_menu)
    elif message.text == START_KEYBOARD_DISHES_OF_THE_WEEK:
        for week_dish in config.MENU_OF_THE_WEEK:
            week_dish.send_as_message(bot, message.chat.id)
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
    elif message.text == START_KEYBOARD_CART:
        send_cart(bot, message)
    elif message.text == START_KEYBOARD_HELP:
        bot.send_message(
            message.chat.id,
            "Мы очень надеемся, что вы справитесь без инструкции",
            reply_markup=START_KEYBOARD,
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
