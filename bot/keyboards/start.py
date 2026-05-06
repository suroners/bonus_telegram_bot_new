from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard(translator):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(translator.t("start.button.geo"), callback_data="start:geo"),
                InlineKeyboardButton(translator.t("start.button.bonuses"), callback_data="start:bonuses"),
            ],
            [
                InlineKeyboardButton(translator.t("start.button.settings"), callback_data="start:settings"),
                InlineKeyboardButton(translator.t("start.button.subscribe"), callback_data="start:subscribe"),
            ],
        ]
    )
