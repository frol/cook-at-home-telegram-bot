import collections
import dataclasses
import decimal
import pathlib

import telebot

from config import TELEGRAM_TOKEN

telebot.apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(TELEGRAM_TOKEN)

ADMIN_CHAT_ID = 202396153

KEYBOARD_BACK = "Назад"

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

CATEGORIES = {
    "Необычное": ["Хуммус", "Вареники с картохой"],
    "Easy": ["Паста с сыром"],
}

DISHES_OF_THE_WEEK = ["Хуммус"]


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


DISHES_FOLDER = pathlib.Path("./dishes")
DISHES = {dish.name: dish for dish in load_dishes(DISHES_FOLDER)}


def load_menu():
    return {
        dish_category: [DISHES[dish_name] for dish_name in dish_names]
        for dish_category, dish_names in CATEGORIES.items()
    }


MENU = load_menu()
MENU_OF_THE_WEEK = [DISHES[dish_name] for dish_name in DISHES_OF_THE_WEEK]

MENU_KEYBOARD = telebot.types.ReplyKeyboardMarkup()
MENU_KEYBOARD.row_width = 2
MENU_KEYBOARD.add(
    *[telebot.types.KeyboardButton(menu_type) for menu_type in MENU.keys()]
)
MENU_KEYBOARD.row(telebot.types.KeyboardButton(KEYBOARD_BACK))


class Cart:
    def __init__(self):
        self.total = decimal.Decimal(0)
        self.delivery_address = ""
        self.contact_info = ""
        self._items = collections.defaultdict(lambda: 0)

    def __contains__(self, dish_name):
        return dish_name in self._items

    def __getitem__(self, dish_name):
        return self._items[dish_name]

    def __setitem__(self, dish_name, dish_count):
        self._items[dish_name] = dish_count
        self.update_total()

    def items(self):
        return self._items.items()

    def update_total(self):
        self.total = sum(
            DISHES[dish_name].get_price() * dish_count
            for dish_name, dish_count in self.items()
        )

    def get_confirmation_text(self):
        return f"Я подтверждаю заказ на сумму {self.total:.2f} грн."


CARTS = collections.defaultdict(Cart)

CART_KEYBOARD_GO_TO_ORDER = "Перейти к оформлению заказа"


def send_cart(message):
    cart = CARTS[message.chat.id]
    if not any(dish_count for _, dish_count in cart.items()):
        bot.send_message(
            message.chat.id, "Ваша корзина пуста", reply_markup=START_KEYBOARD
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
        return
    bot.send_message(message.chat.id, "Ваша корзина:")

    for dish_name, dish_count in cart.items():
        if dish_count == 0:
            continue
        dish = DISHES[dish_name]
        cart_dish_keyboard = telebot.types.InlineKeyboardMarkup()
        cart_dish_keyboard.row_width = 4
        cart_dish_keyboard.add(
            telebot.types.InlineKeyboardButton(f"-", callback_data="-"),
            telebot.types.InlineKeyboardButton(
                f"{dish_count} ({dish.get_price() * dish_count:.2f} грн.)",
                callback_data="_",
            ),
            telebot.types.InlineKeyboardButton(f"+", callback_data="+"),
            telebot.types.InlineKeyboardButton(f"Удалить", callback_data="remove"),
        )
        bot.send_photo(
            message.chat.id,
            photo=dish.get_photo(),
            caption=f"*{dish.name}*\n{dish.get_price():.2f} грн.",
            reply_markup=cart_dish_keyboard,
            parse_mode="Markdown",
        )

    confirmation_keyboard = telebot.types.ReplyKeyboardMarkup()
    confirmation_keyboard.add(
        telebot.types.KeyboardButton(CART_KEYBOARD_GO_TO_ORDER),
        telebot.types.KeyboardButton(KEYBOARD_BACK),
    )
    bot.send_message(
        message.chat.id,
        f"К оплате {cart.total:.2f} грн. После подтверждения заказа, в чат присоединится оператор.",
        reply_markup=confirmation_keyboard,
    )
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_order_begin)


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


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Приступим", reply_markup=START_KEYBOARD)
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_start)


def handle_start(message):
    if message.text == START_KEYBOARD_MENU:
        bot.send_message(
            message.chat.id, START_KEYBOARD_MENU, reply_markup=MENU_KEYBOARD
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_menu)
    elif message.text == START_KEYBOARD_DISHES_OF_THE_WEEK:
        for dish in MENU_OF_THE_WEEK:
            dish.send_as_message(bot, message.chat.id)
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
    elif message.text == START_KEYBOARD_CART:
        send_cart(message)
    elif message.text == START_KEYBOARD_HELP:
        bot.send_message(
            message.chat.id,
            "Мы очень надеемся, что вы справитесь без инструкции",
            reply_markup=START_KEYBOARD,
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("dish_what_you_get__")
)
def callback_dish_what_you_get(call):
    dish_name = call.data[len("dish_what_you_get__") :]
    dish = DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return
    bot.answer_callback_query(call.id, f"Посмотрим, что же вы получите с {dish.name}")
    dish_markup = telebot.types.InlineKeyboardMarkup()
    dish_markup.row_width = 1
    dish_markup.add(
        telebot.types.InlineKeyboardButton(
            "Должно быть дома", callback_data=f"dish_what_you_need__{dish.name}"
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
    dish = DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return
    bot.answer_callback_query(call.id, f"Чтобы приготовить {dish.name} вам нужно...")
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


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("dish_add_to_cart__")
)
def callback_dish_add_to_cart(call):
    dish_info = call.data[len("dish_add_to_cart__") :].split("__", 2)
    dish_name = dish_info[0]
    if len(dish_info) == 1:
        dish_count = CARTS[call.message.chat.id][dish_name]
    else:
        try:
            dish_count = int(dish_info[1])
        except ValueError:
            dish_count = 0
    dish = DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return
    if dish_count != 0:
        CARTS[call.message.chat.id][dish_name] = dish_count
    bot.answer_callback_query(call.id, f"Да-да, {dish.name}")
    cart_keyboard = telebot.types.InlineKeyboardMarkup()
    cart_keyboard.row_width = 2
    in_cart = (
        lambda title, count: title if count != dish_count else f"{title} (в корзине)"
    )
    cart_keyboard.add(
        telebot.types.InlineKeyboardButton(
            in_cart("На 1 персону", 1),
            callback_data=f"dish_add_to_cart__{dish.name}__1",
        ),
        telebot.types.InlineKeyboardButton(
            in_cart("На 2 персоны", 2),
            callback_data=f"dish_add_to_cart__{dish.name}__2",
        ),
        telebot.types.InlineKeyboardButton(
            in_cart("На 3 персоны", 3),
            callback_data=f"dish_add_to_cart__{dish.name}__3",
        ),
        telebot.types.InlineKeyboardButton(
            in_cart("На 4 персоны", 4),
            callback_data=f"dish_add_to_cart__{dish.name}__4",
        ),
    )
    if dish_count != 0:
        cart_keyboard.add(
            telebot.types.InlineKeyboardButton(
                "Перейти к корзине", callback_data=f"cart",
            )
        )
    if len(dish_info) == 1:
        bot.send_message(
            call.message.chat.id,
            f"На сколько персон вы хотите приготовить {dish.name}?",
            reply_markup=cart_keyboard,
            parse_mode="Markdown",
        )
    else:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=cart_keyboard
        )


def handle_menu(message):
    menu_item = message.text
    if menu_item == KEYBOARD_BACK:
        return start(message)

    if menu_item not in MENU:
        bot.send_message(
            message.chat.id, START_KEYBOARD_MENU, reply_markup=MENU_KEYBOARD
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_menu)
        return

    for dish in MENU[menu_item]:
        dish.send_as_message(bot, message.chat.id)
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_menu)


@bot.callback_query_handler(func=lambda call: call.data == "cart")
def callback_cart(call):
    return send_cart(call.message)


def handle_order_begin(message):
    if message.text == CART_KEYBOARD_GO_TO_ORDER:
        bot.send_message(
            message.chat.id,
            f"Введите адрес доставки (улица, дом, подъезд, домофон, этаж, номер квартиры):",
            reply_markup=telebot.types.ReplyKeyboardRemove(),
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_address_input)
        return
    return start(message)


def handle_address_input(message):
    if message.chat.id not in CARTS:
        bot.send_message(message.chat.id, f"Вы ещё ничего не заказали.")
        return start(message)
    CARTS[message.chat.id].delivery_address = message.text
    bot.send_message(
        message.chat.id,
        f"Введите контактные данные (номер телефона), чтобы курьер мог оперативно связаться с вами:",
        reply_markup=telebot.types.ReplyKeyboardRemove(),
    )
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_contact_info_input)


def handle_contact_info_input(message):
    if message.chat.id not in CARTS:
        bot.send_message(message.chat.id, f"Вы ещё ничего не заказали.")
        return start(message)
    cart = CARTS[message.chat.id]
    cart.contact_info = message.text

    confirmation_keyboard = telebot.types.ReplyKeyboardMarkup()
    confirmation_keyboard.add(
        telebot.types.KeyboardButton(cart.get_confirmation_text()),
        telebot.types.KeyboardButton(KEYBOARD_BACK),
    )

    bot.send_message(
        message.chat.id,
        f"Подтвердите Ваш заказ на сумму {cart.total:.2f} грн.\n\n"
        f"Адрес доставки: {cart.delivery_address}\n"
        f"Контактные данные: {cart.contact_info}",
        reply_markup=confirmation_keyboard,
    )
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_order_confirmation)


def handle_order_confirmation(message):
    if message.text == KEYBOARD_BACK:
        return send_cart(message)
    if message.chat.id not in CARTS:
        bot.send_message(message.chat.id, f"Вы ещё ничего не заказали.")
        return start(message)
    cart = CARTS[message.chat.id]
    if message.text == cart.get_confirmation_text():
        bot.send_message(
            ADMIN_CHAT_ID,
            f"НОВЫЙ ЗАКАЗ! Чат #{message.chat.id}\n\n"
            + "\n".join(
                f"* {dish_name} (x{dish_count})"
                for dish_name, dish_count in cart.items()
            )
            + f"\n\nИтого: {cart.total:.2f} грн.\n"
            f"Адрес доставки: {cart.delivery_address}\n"
            f"Контактная информация: {cart.contact_info}",
        )
        bot.send_message(
            message.chat.id,
            "Ваш заказ отправлен в обработку!",
            reply_markup=START_KEYBOARD,
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
        del CARTS[message.chat.id]
        return
    return start(message)


bot.polling(none_stop=True)
print("Bye.")
