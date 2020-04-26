import dataclasses
import decimal
import pathlib

import telebot

from . import config
from .config import bot


@dataclasses.dataclass
class Dish:
    folder: pathlib.Path
    name: str

    def get_price(self):
        with open(self.folder / "price.txt") as price_file:
            return decimal.Decimal(price_file.read().strip())

    def get_description(self):
        with open(self.folder / "description.txt") as description_file:
            return description_file.read()

    def get_what_you_get(self):
        with open(self.folder / "what_you_get.txt") as what_you_get_file:
            return what_you_get_file.read()

    def get_what_you_need(self):
        with open(self.folder / "what_you_need.txt") as what_you_need_file:
            return what_you_need_file.read()

    def get_photo(self):
        return open(self.folder / "photo.jpg", "rb")

    def send_as_message(self, bot, chat_id):
        dish_markup = telebot.types.InlineKeyboardMarkup()
        dish_markup.row_width = 1
        dish_markup.add(
            telebot.types.InlineKeyboardButton(
                "Вы получите", callback_data=f"dish_what_you_get__{self.name}"
            ),
            telebot.types.InlineKeyboardButton(
                "Должно быть дома", callback_data=f"dish_what_you_need__{self.name}"
            ),
            telebot.types.InlineKeyboardButton(
                "В корзину", callback_data=f"dish_add_to_cart__{self.name}"
            ),
        )

        return bot.send_photo(
            chat_id,
            photo=self.get_photo(),
            caption=f"*{self.name}*\n{self.get_price():.2f} грн.\n\n{self.get_description()}",
            reply_markup=dish_markup,
            parse_mode="Markdown",
        )


def load_dishes(folder):
    for dish_folder in folder.iterdir():
        yield Dish(folder=dish_folder, name=dish_folder.name)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("dish_what_you_get__")
)
def callback_dish_what_you_get(call):
    dish_name = call.data[len("dish_what_you_get__") :]
    dish = config.DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return
    bot.answer_callback_query(call.id, f"Посмотрим, что же вы получите с {dish.name}")
    dish_markup = telebot.types.InlineKeyboardMarkup()
    dish_markup.row_width = 1
    dish_markup.add(
        telebot.types.InlineKeyboardButton(
            "Должно быть дома", callback_data=f"dish_what_you_need__{dish.name}",
        ),
        telebot.types.InlineKeyboardButton(
            "В корзину", callback_data=f"dish_add_to_cart__{dish.name}"
        ),
    )
    bot.send_message(
        call.message.chat.id,
        f"*{dish.name}*\n\n{dish.get_what_you_get()}",
        reply_markup=dish_markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("dish_what_you_need__")
)
def callback_dish_what_you_need(call):
    dish_name = call.data[len("dish_what_you_need__") :]
    dish = config.DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return
    bot.answer_callback_query(
        call.id, f"Чтобы приготовить {dish.name} вам понадобятся..."
    )
    dish_markup = telebot.types.InlineKeyboardMarkup()
    dish_markup.row_width = 1
    dish_markup.add(
        telebot.types.InlineKeyboardButton(
            "Вы получите", callback_data=f"dish_what_you_get__{dish.name}"
        ),
        telebot.types.InlineKeyboardButton(
            "В корзину", callback_data=f"dish_add_to_cart__{dish.name}"
        ),
    )
    bot.send_message(
        call.message.chat.id,
        f"**{dish.name}**\n\n{dish.get_what_you_need()}",
        reply_markup=dish_markup,
        parse_mode="Markdown",
    )
