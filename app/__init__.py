import collections
import pathlib

from .config import bot


@bot.middleware_handler(
    update_types=[
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
        "inline_query",
        "chosen_inline_result",
        "callback_query",
        "shipping_query",
        "pre_checkout_query",
        "poll",
    ]
)
def inspect_middleware(bot_instance, message):
    print(message)


from . import common
from . import config
from . import start
from . import menu
from . import dish
from . import cart
from . import storage

bot.polling(none_stop=True)
