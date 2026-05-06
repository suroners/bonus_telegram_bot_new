from asgiref.sync import sync_to_async

from bonus_core.models import Geo, TelegramUser, UserSettings


class TelegramUserService:
    LANGUAGE_GEO_FALLBACKS = {
        "en": "uk",
        "fr": "fr",
        "ro": "ro",
        "fi": "fi",
        "da": "dk",
        "et": "ee",
        "nl": "nl",
        "sv": "se",
        "mt": "mt",
    }
    GEO_ALIASES = {
        "gb": "uk",
    }

    @staticmethod
    async def register(telegram_user):
        return await sync_to_async(TelegramUserService._register)(telegram_user)

    @classmethod
    def _register(cls, telegram_user):
        language_code = (telegram_user.language_code or "").lower()
        user, created = TelegramUser.objects.update_or_create(
            telegram_id=telegram_user.id,
            defaults={
                "username": telegram_user.username,
                "first_name": telegram_user.first_name,
                "last_name": telegram_user.last_name,
            },
        )
        user_settings, _ = UserSettings.objects.get_or_create(user=user)
        if language_code and (created or not user_settings.preferred_language):
            user_settings.preferred_language = language_code
            user_settings.save(update_fields=["preferred_language", "updated_at"])
        if not user.geo_id:
            inferred_geo = cls._infer_geo_from_language(language_code)
            if inferred_geo:
                user.geo = inferred_geo
                user.save(update_fields=["geo", "updated_at"])
        return user

    @staticmethod
    async def set_geo(telegram_id, geo_code):
        return await sync_to_async(TelegramUserService._set_geo)(telegram_id, geo_code)

    @staticmethod
    def _set_geo(telegram_id, geo_code):
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        user.geo = Geo.objects.get(code=geo_code)
        user.save(update_fields=["geo", "updated_at"])
        return user

    @staticmethod
    async def get_profile(telegram_id):
        return await sync_to_async(TelegramUserService._get_profile)(telegram_id)

    @staticmethod
    def _get_profile(telegram_id):
        user = TelegramUser.objects.select_related("geo", "settings").get(telegram_id=telegram_id)
        settings = user.settings
        return {
            "telegram_id": user.telegram_id,
            "geo_code": user.geo.code if user.geo_id else None,
            "geo_name": user.geo.name if user.geo_id else None,
            "preferred_language": settings.preferred_language,
            "notify_enabled": settings.notify_enabled,
            "receive_crypto_bonuses": settings.receive_crypto_bonuses,
            "receive_freespins": settings.receive_freespins,
            "receive_deposit_bonuses": settings.receive_deposit_bonuses,
        }

    @classmethod
    def _infer_geo_from_language(cls, language_code):
        normalized = (language_code or "").strip().lower().replace("_", "-")
        if not normalized:
            return None

        parts = [part for part in normalized.split("-") if part]
        if len(parts) > 1:
            region_code = cls.GEO_ALIASES.get(parts[-1], parts[-1])
            geo = Geo.objects.filter(code=region_code, is_active=True).first()
            if geo:
                return geo

        fallback_code = cls.LANGUAGE_GEO_FALLBACKS.get(parts[0])
        if not fallback_code:
            return None
        fallback_code = cls.GEO_ALIASES.get(fallback_code, fallback_code)
        return Geo.objects.filter(code=fallback_code, is_active=True).first()
