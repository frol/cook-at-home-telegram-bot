from . import common, config, start
from .config import bot


def handle_menu(message):
    menu_item = message.text
    if menu_item == common.KEYBOARD_BACK:
        return start.start(message)

    if menu_item not in config.MENU:
        bot.send_message(
            message.chat.id,
            start.START_KEYBOARD_MENU,
            reply_markup=config.MENU_KEYBOARD,
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_menu)
        return

    for menu_dish in config.MENU[menu_item]:
        menu_dish.send_as_message(bot, message.chat.id)
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_menu)
