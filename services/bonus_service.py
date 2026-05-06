from django.conf import settings
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.utils import timezone

from bonus_core.models import Bonus, Casino, TelegramUser
from bonus_core.services.bonus_link_service import BonusLinkService


class TelegramBonusService:
    NO_GEO_MODE_TOP_PER_CASINO = "top_per_casino"

    @staticmethod
    async def top_bonus_cards(telegram_id, limit=10):
        return await sync_to_async(TelegramBonusService._top_bonus_cards)(telegram_id, limit)

    @classmethod
    def _top_bonus_cards(cls, telegram_id, limit=10):
        user = cls._user(telegram_id)
        bonuses = cls._selected_bonuses(user, limit=limit)
        return [cls._card(bonus) for bonus in bonuses]

    @staticmethod
    async def casino_bonus_cards(telegram_id, casino_name, limit=10):
        return await sync_to_async(TelegramBonusService._casino_bonus_cards)(telegram_id, casino_name, limit)

    @classmethod
    def _casino_bonus_cards(cls, telegram_id, casino_name, limit=10):
        user = cls._user(telegram_id)
        casino = cls._matching_casino(casino_name)
        if not casino:
            similar = list(Casino.objects.filter(name__icontains=casino_name[:3]).order_by("name").values_list("name", flat=True)[:5])
            return {"found": False, "similar": similar}
        bonuses = cls._bonuses_for_casino(user, casino, limit=limit)
        return {"found": True, "casino": casino.name, "bonuses": [cls._card(bonus) for bonus in bonuses]}

    @staticmethod
    def _user(telegram_id):
        return TelegramUser.objects.select_related("geo", "settings").get(telegram_id=telegram_id)

    @staticmethod
    def _matching_casino(casino_name):
        return Casino.objects.filter(name__icontains=casino_name).order_by("-priority", "name").first()

    @classmethod
    def _selected_bonuses(cls, user, limit=10):
        limit = max(int(limit or 0), 1)
        if user.geo_id or cls._no_geo_mode() != cls.NO_GEO_MODE_TOP_PER_CASINO:
            return list(cls._eligible_queryset(user)[:limit])
        return cls._no_geo_bonuses(
            user,
            casino_limit=min(limit, cls._no_geo_casino_limit()),
            per_casino_limit=cls._no_geo_bonus_per_casino_limit(),
        )

    @classmethod
    def _bonuses_for_casino(cls, user, casino, limit=10):
        queryset = cls._eligible_queryset(user, ignore_geo=not user.geo_id).filter(casino=casino)
        if not user.geo_id:
            limit = min(max(int(limit or 0), 1), cls._no_geo_casino_command_limit())
        return list(queryset.order_by("-priority", "-created_at", "-id")[:limit])

    @classmethod
    def _eligible_queryset(cls, user, ignore_geo=False, order_for_no_geo=False):
        today = timezone.localdate()
        queryset = Bonus.objects.select_related("casino", "geo", "provider", "game").filter(
            is_active=True,
            is_approved=True,
        )
        queryset = queryset.filter(Q(start_date__isnull=True) | Q(start_date__lte=today))
        queryset = queryset.filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        queryset = cls._apply_settings_filters(queryset, user.settings)
        if user.geo_id and not ignore_geo:
            geo_ids = [user.geo_id]
            if user.geo.parent_id:
                geo_ids.append(user.geo.parent_id)
            queryset = queryset.filter(Q(geo_id__in=geo_ids) | Q(geo__isnull=True))
        if order_for_no_geo:
            return queryset.order_by("-casino__priority", "casino_id", "-priority", "-created_at", "-id")
        return queryset.order_by("-priority", "-casino__priority", "-created_at", "-id")

    @staticmethod
    def _apply_settings_filters(queryset, user_settings):
        if not user_settings.receive_crypto_bonuses:
            queryset = queryset.exclude(
                Q(currency__icontains="btc")
                | Q(currency__icontains="eth")
                | Q(currency__icontains="usdt")
                | Q(currency__icontains="usdc")
                | Q(type__icontains="crypto")
            )
        if not user_settings.receive_freespins:
            queryset = queryset.exclude(Q(type__icontains="free spin") | Q(title__icontains="free spin"))
        if not user_settings.receive_deposit_bonuses:
            queryset = queryset.exclude(Q(type__icontains="deposit") | Q(title__icontains="deposit"))
        return queryset

    @staticmethod
    def _matches_user_settings(bonus, user_settings):
        bonus_type = (bonus.type or "").lower()
        title = (bonus.title or "").lower()
        currency = (bonus.currency or "").lower()
        if not user_settings.receive_crypto_bonuses and ("crypto" in bonus_type or currency in {"btc", "eth", "usdt", "usdc"}):
            return False
        if not user_settings.receive_freespins and ("free spin" in bonus_type or "free spin" in title):
            return False
        if not user_settings.receive_deposit_bonuses and ("deposit" in bonus_type or "deposit" in title):
            return False
        return True

    @staticmethod
    def _bonus_matches_user_geo(bonus, user):
        if not user.geo_id or not bonus.geo_id:
            return True
        geo_ids = {user.geo_id}
        if user.geo and user.geo.parent_id:
            geo_ids.add(user.geo.parent_id)
        return bonus.geo_id in geo_ids

    @classmethod
    def _is_bonus_in_no_geo_selection(cls, user, bonus):
        if user.geo_id or cls._no_geo_mode() != cls.NO_GEO_MODE_TOP_PER_CASINO:
            return False
        selected_ids = {
            selected_bonus.id
            for selected_bonus in cls._no_geo_bonuses(
                user,
                casino_limit=cls._no_geo_casino_limit(),
                per_casino_limit=cls._no_geo_bonus_per_casino_limit(),
            )
        }
        return bonus.id in selected_ids

    @classmethod
    def _no_geo_bonuses(cls, user, casino_limit=None, per_casino_limit=None):
        casino_limit = max(int(casino_limit or cls._no_geo_casino_limit()), 1)
        per_casino_limit = max(int(per_casino_limit or cls._no_geo_bonus_per_casino_limit()), 1)
        queryset = cls._eligible_queryset(user, ignore_geo=True, order_for_no_geo=True)

        selected = []
        casino_counts = {}
        for bonus in queryset:
            count = casino_counts.get(bonus.casino_id)
            if count is None:
                if len(casino_counts) >= casino_limit:
                    break
                casino_counts[bonus.casino_id] = 0
                count = 0
            if count >= per_casino_limit:
                continue
            selected.append(bonus)
            casino_counts[bonus.casino_id] = count + 1
        return selected

    @staticmethod
    def _no_geo_mode():
        value = (getattr(settings, "TELEGRAM_NO_GEO_MODE", TelegramBonusService.NO_GEO_MODE_TOP_PER_CASINO) or "").strip()
        return value or TelegramBonusService.NO_GEO_MODE_TOP_PER_CASINO

    @staticmethod
    def _no_geo_casino_limit():
        return max(int(getattr(settings, "TELEGRAM_NO_GEO_CASINO_LIMIT", 3)), 1)

    @staticmethod
    def _no_geo_bonus_per_casino_limit():
        return max(int(getattr(settings, "TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT", 1)), 1)

    @staticmethod
    def _no_geo_casino_command_limit():
        return max(int(getattr(settings, "TELEGRAM_NO_GEO_CASINO_COMMAND_LIMIT", 3)), 1)

    @staticmethod
    def _card(bonus):
        return {
            "id": bonus.id,
            "title": bonus.title,
            "description": bonus.description,
            "type": bonus.type,
            "casino": bonus.casino.name,
            "geo": bonus.geo.code.upper() if bonus.geo_id else "GLOBAL",
            "currency": bonus.currency,
            "url": BonusLinkService.resolve_bonus_url(bonus),
        }
