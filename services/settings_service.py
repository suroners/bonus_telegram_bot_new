from asgiref.sync import sync_to_async

from bonus_core.models import TelegramUser
from bonus_telegram_bot.i18n import TelegramI18nService, normalize_locale


class TelegramSettingsService:
    SUPPORTED_CURRENCIES = ("USD", "EUR", "GBP", "RUB")
    TOGGLE_FIELDS = {
        "notify": "notify_enabled",
        "crypto": "receive_crypto_bonuses",
        "freespins": "receive_freespins",
        "deposit": "receive_deposit_bonuses",
    }

    @staticmethod
    async def snapshot(telegram_id):
        return await sync_to_async(TelegramSettingsService._snapshot)(telegram_id)

    @staticmethod
    def _snapshot(telegram_id):
        user = TelegramUser.objects.select_related("settings").get(telegram_id=telegram_id)
        settings = user.settings
        return {
            "notify_enabled": settings.notify_enabled,
            "preferred_currency": settings.preferred_currency,
            "preferred_language": settings.preferred_language,
            "receive_crypto_bonuses": settings.receive_crypto_bonuses,
            "receive_freespins": settings.receive_freespins,
            "receive_deposit_bonuses": settings.receive_deposit_bonuses,
        }

    @staticmethod
    async def toggle(telegram_id, key):
        return await sync_to_async(TelegramSettingsService._toggle)(telegram_id, key)

    @staticmethod
    def _toggle(telegram_id, key):
        field = TelegramSettingsService.TOGGLE_FIELDS[key]
        user = TelegramUser.objects.select_related("settings").get(telegram_id=telegram_id)
        settings = user.settings
        setattr(settings, field, not getattr(settings, field))
        settings.save(update_fields=[field, "updated_at"])
        return TelegramSettingsService._snapshot(telegram_id)

    @staticmethod
    async def set_currency(telegram_id, currency):
        return await sync_to_async(TelegramSettingsService._set_currency)(telegram_id, currency)

    @staticmethod
    def _set_currency(telegram_id, currency):
        user = TelegramUser.objects.select_related("settings").get(telegram_id=telegram_id)
        settings = user.settings
        normalized = (currency or "").strip().lower()
        if normalized in {"", "none", "unset", "null"}:
            settings.preferred_currency = None
        else:
            settings.preferred_currency = currency.upper()
        settings.save(update_fields=["preferred_currency", "updated_at"])
        return TelegramSettingsService._snapshot(telegram_id)

    @staticmethod
    async def set_language(telegram_id, language):
        return await sync_to_async(TelegramSettingsService._set_language)(telegram_id, language)

    @staticmethod
    def _set_language(telegram_id, language):
        user = TelegramUser.objects.select_related("settings").get(telegram_id=telegram_id)
        settings = user.settings
        settings.preferred_language = normalize_locale(language) or TelegramI18nService.resolve_locale()
        settings.save(update_fields=["preferred_language", "updated_at"])
        return TelegramSettingsService._snapshot(telegram_id)

    @staticmethod
    def supported_languages():
        return TelegramI18nService.supported_locales()

    @staticmethod
    def supported_currencies():
        return TelegramSettingsService.SUPPORTED_CURRENCIES
