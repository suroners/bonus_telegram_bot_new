from telegram import KeyboardButton, ReplyKeyboardMarkup

from bonus_telegram_bot.i18n import TelegramI18nService


ACTION_MESSAGE_KEYS = {
    "home": "global.button.home",
    "bonuses": "global.button.bonuses",
    "geo": "global.button.geo",
    "settings": "global.button.settings",
}


def global_navigation_keyboard(translator):
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(translator.t(ACTION_MESSAGE_KEYS["home"])),
                KeyboardButton(translator.t(ACTION_MESSAGE_KEYS["bonuses"])),
            ],
            [
                KeyboardButton(translator.t(ACTION_MESSAGE_KEYS["geo"])),
                KeyboardButton(translator.t(ACTION_MESSAGE_KEYS["settings"])),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )


def global_navigation_action(text):
    normalized = (text or "").strip()
    if not normalized:
        return None

    for locale_code in TelegramI18nService.supported_locales():
        translator = TelegramI18nService.translator(preferred_language=locale_code)
        for action, message_key in ACTION_MESSAGE_KEYS.items():
            if normalized == translator.t(message_key):
                return action
    return None


async def send_global_navigation_message(message, translator):
    await message.reply_text(
        translator.t("global.keyboard.hint"),
        reply_markup=global_navigation_keyboard(translator),
    )
