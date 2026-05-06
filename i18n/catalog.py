from bonus_telegram_bot.i18n.locales.en import MESSAGES as EN_MESSAGES
from bonus_telegram_bot.i18n.locales.ru import MESSAGES as RU_MESSAGES


DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = {
    "en": {"endonym": "English"},
    "ru": {"endonym": "Русский"},
}
CATALOGS = {
    "en": EN_MESSAGES,
    "ru": RU_MESSAGES,
}
