from dataclasses import dataclass

from asgiref.sync import sync_to_async

from bonus_core.models import TelegramUser
from bonus_telegram_bot.i18n.catalog import CATALOGS, DEFAULT_LOCALE, SUPPORTED_LOCALES


def normalize_locale(value):
    normalized = (value or "").strip().lower().replace("_", "-")
    if not normalized:
        return None
    primary = normalized.split("-", 1)[0]
    if primary in SUPPORTED_LOCALES:
        return primary
    return None


@dataclass(frozen=True)
class TelegramTranslator:
    locale: str = DEFAULT_LOCALE

    def t(self, key, **kwargs):
        template = CATALOGS.get(self.locale, {}).get(key)
        if template is None:
            template = CATALOGS[DEFAULT_LOCALE].get(key)
        if template is None:
            raise KeyError("Missing translation key: %s" % key)
        if kwargs:
            return template.format(**kwargs)
        return template

    def locale_label(self, locale_code):
        normalized = normalize_locale(locale_code) or DEFAULT_LOCALE
        return SUPPORTED_LOCALES[normalized]["endonym"]

    def currency_label(self, currency_code):
        return currency_code.upper() if currency_code else self.t("settings.currency.unset")

    def settings_toggle_label(self, key, enabled):
        state = self.t("common.on" if enabled else "common.off")
        return self.t("settings.toggle.%s" % key, state=state)


class TelegramI18nService:
    @staticmethod
    def translator(preferred_language=None, telegram_language_code=None):
        locale = TelegramI18nService.resolve_locale(preferred_language, telegram_language_code)
        return TelegramTranslator(locale=locale)

    @staticmethod
    async def for_user(telegram_id, telegram_language_code=None):
        return await sync_to_async(TelegramI18nService._for_user)(telegram_id, telegram_language_code)

    @staticmethod
    def _for_user(telegram_id, telegram_language_code=None):
        preferred_language = (
            TelegramUser.objects.select_related("settings")
            .values_list("settings__preferred_language", flat=True)
            .get(telegram_id=telegram_id)
        )
        return TelegramI18nService.translator(
            preferred_language=preferred_language,
            telegram_language_code=telegram_language_code,
        )

    @staticmethod
    def resolve_locale(preferred_language=None, telegram_language_code=None):
        return (
            normalize_locale(preferred_language)
            or normalize_locale(telegram_language_code)
            or DEFAULT_LOCALE
        )

    @staticmethod
    def supported_locales():
        return tuple(SUPPORTED_LOCALES.keys())

    @staticmethod
    def catalog_keys():
        return set(CATALOGS[DEFAULT_LOCALE].keys())
