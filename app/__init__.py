import collections
import pathlib

from .config import bot

from . import common
from . import config
from . import start
from . import menu
from . import dish
from . import cart
from . import storage


@bot.message_handler()
def handle_non_handled_message(message):
    return start.start(message)


# Enable saving next step handlers to file "./.handlers-saves/step.save".
# Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
# saving will hapen after delay 2 seconds.
bot.enable_save_next_step_handlers(delay=2)

# Load next_step_handlers from save file (default "./.handlers-saves/step.save")
# WARNING It will work only if enable_save_next_step_handlers was called!
bot.load_next_step_handlers()

while True:
    bot.polling(none_stop=True)
