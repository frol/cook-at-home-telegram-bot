import dataclasses
import decimal

import telebot

from . import common, config
from .config import bot
from .dish import Dish


@dataclasses.dataclass
class CartDish:
    dish: Dish
    count: int


class Cart:
    def __init__(self):
        self.total = decimal.Decimal(0)
        self.delivery_address = ""
        self.contact_info = ""
        self._items = {}

    def __contains__(self, dish_name):
        return dish_name in self._items

    def __getitem__(self, dish_name):
        return self._items[dish_name]

    def __setitem__(self, dish_name, cart_dish):
        self._items[dish_name] = cart_dish
        self.update_total()

    def values(self):
        return self._items.values()

    def update_total(self):
        self.total = sum(
            cart_dish.dish.get_price() * cart_dish.count for cart_dish in self.values()
        )
        
    def get_confirmation_text(self):
        return f"Я подтверждаю заказ на сумму {self.total:.2f} грн."


CART_KEYBOARD_GO_TO_ORDER = "Перейти к оформлению заказа"


def send_cart(bot, message):
    from .start import START_KEYBOARD, handle_start
    from .storage import CARTS

    cart = CARTS[message.chat.id]
    if not any(cart_dish.count for cart_dish in cart.values()):
        bot.send_message(
            message.chat.id, "Ваша корзина пуста", reply_markup=START_KEYBOARD
        )
        bot.clear_step_handler(message)
        bot.register_next_step_handler(message, handle_start)
        return
    bot.send_message(message.chat.id, "Ваша корзина:")

    for cart_dish in cart.values():
        if cart_dish.count == 0:
            continue
        cart_dish_keyboard = telebot.types.InlineKeyboardMarkup()
        cart_dish_keyboard.row_width = 4
        cart_dish_keyboard.add(
            telebot.types.InlineKeyboardButton(f"-", callback_data="-"),
            telebot.types.InlineKeyboardButton(
                f"{cart_dish.count} ({cart_dish.dish.get_price() * cart_dish.count:.2f} грн.)",
                callback_data="_",
            ),
            telebot.types.InlineKeyboardButton(f"+", callback_data="+"),
            telebot.types.InlineKeyboardButton(f"Удалить", callback_data="remove"),
        )
        bot.send_photo(
            message.chat.id,
            photo=cart_dish.dish.get_photo(),
            caption=f"*{cart_dish.dish.name}*\n{cart_dish.dish.get_price():.2f} грн.",
            reply_markup=cart_dish_keyboard,
            parse_mode="Markdown",
        )

    confirmation_keyboard = telebot.types.ReplyKeyboardMarkup()
    confirmation_keyboard.add(
        telebot.types.KeyboardButton(CART_KEYBOARD_GO_TO_ORDER),
        telebot.types.KeyboardButton(common.KEYBOARD_BACK),
    )
    bot.send_message(
        message.chat.id,
        f"К оплате {cart.total:.2f} грн. После подтверждения заказа, в чат присоединится оператор.",
        reply_markup=confirmation_keyboard,
    )
    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, handle_order_begin)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("dish_add_to_cart__")
)
def callback_dish_add_to_cart(call):
    from .storage import CARTS

    dish_info = call.data[len("dish_add_to_cart__") :].split("__", 2)
    dish_name = dish_info[0]
    dish = config.DISHES.get(dish_name)
    if dish is None:
        bot.answer_callback_query(call.id, f"Ой, мы потеряли {dish_name}")
        return

    cart = CARTS[call.message.chat.id]
    if dish.name not in cart:
        cart_dish = cart[dish.name] = CartDish(dish, 0)
    else:
        cart_dish = cart[dish_name]
    if len(dish_info) == 2:
        try:
            cart_dish.count = int(dish_info[1])
            cart.update_total()
        except ValueError:
            pass
    bot.answer_callback_query(call.id, f"Да-да, {dish.name}")
    cart_keyboard = telebot.types.InlineKeyboardMarkup()
    cart_keyboard.row_width = 2
    in_cart = (
        lambda title, count: title
        if count != cart_dish.count
        else f"{title} (в корзине)"
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
    if cart_dish.count != 0:
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


@bot.callback_query_handler(func=lambda call: call.data == "cart")
def callback_cart(call):
    return send_cart(bot, call.message)


def handle_order_begin(message):
    from .start import start

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
    from .start import start
    from .storage import CARTS

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
    from .start import start
    from .storage import CARTS

    if message.chat.id not in CARTS:
        bot.send_message(message.chat.id, f"Вы ещё ничего не заказали.")
        return start(message)
    cart = CARTS[message.chat.id]
    cart.contact_info = message.text

    confirmation_keyboard = telebot.types.ReplyKeyboardMarkup()
    confirmation_keyboard.add(
        telebot.types.KeyboardButton(cart.get_confirmation_text()),
        telebot.types.KeyboardButton(common.KEYBOARD_BACK),
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
    from .start import START_KEYBOARD, start, handle_start
    from .storage import CARTS

    if message.text == common.KEYBOARD_BACK:
        return send_cart(bot, message)
    if message.chat.id not in CARTS:
        bot.send_message(message.chat.id, f"Вы ещё ничего не заказали.")
        return start(message)
    cart = CARTS[message.chat.id]
    if message.text == cart.get_confirmation_text():
        bot.send_message(
            config.ADMIN_CHAT_ID,
            f"НОВЫЙ ЗАКАЗ! Чат #{message.chat.id}\n\n"
            + "\n".join(
                f"* {cart_dish.dish.name} (x{cart_dish.count})"
                for cart_dish in cart.values()
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
