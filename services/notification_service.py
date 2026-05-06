import asyncio
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from telegram import Bot
from telegram.constants import ParseMode

from bonus_core.models import Bonus, NotificationHistory, NotificationStatus, TelegramUser, UserCasinoSubscription
from bonus_telegram_bot.bot.utils.formatting import format_bonus_cards
from bonus_telegram_bot.services.bonus_service import TelegramBonusService

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    def send_bonus_notifications(self, bonus_id):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
        bonus = Bonus.objects.select_related("casino", "geo").get(id=bonus_id, is_active=True, is_approved=True)
        users = self._eligible_users_for_bonus(bonus)
        sent = 0
        failed = 0
        card = TelegramBonusService._card(bonus)
        message = format_bonus_cards([card])
        for user in users:
            if NotificationHistory.objects.filter(
                user=user,
                bonus_reference_id=bonus.id,
                status=NotificationStatus.SENT,
            ).exists():
                continue
            try:
                asyncio.run(self._send_message(user.telegram_id, message))
                NotificationHistory.objects.update_or_create(
                    user=user,
                    bonus_reference_id=bonus.id,
                    defaults={
                        "bonus": bonus,
                        "casino": bonus.casino,
                        "sent_at": timezone.now(),
                        "status": NotificationStatus.SENT,
                        "error_message": "",
                    },
                )
                sent += 1
            except Exception as exc:  # noqa: BLE001 - keep notification error in DB
                logger.exception("Failed to send bonus %s to user %s", bonus.id, user.telegram_id)
                NotificationHistory.objects.update_or_create(
                    user=user,
                    bonus_reference_id=bonus.id,
                    defaults={
                        "bonus": bonus,
                        "casino": bonus.casino,
                        "sent_at": timezone.now(),
                        "status": NotificationStatus.FAILED,
                        "error_message": str(exc),
                    },
                )
                failed += 1
        return {"sent": sent, "failed": failed}

    def broadcast_daily_top_bonuses(self):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
        users = TelegramUser.objects.select_related("geo", "settings").filter(settings__notify_enabled=True)
        sent = 0
        for user in users:
            cards = TelegramBonusService._top_bonus_cards(user.telegram_id, limit=5)
            if not cards:
                continue
            message = "Daily top bonuses\n\n%s" % format_bonus_cards(cards)
            asyncio.run(self._send_message(user.telegram_id, message))
            sent += 1
        return {"sent": sent}

    def cleanup_old_notifications(self, days=90):
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = NotificationHistory.objects.filter(sent_at__lt=cutoff).delete()
        return {"deleted": deleted}

    def _eligible_users_for_bonus(self, bonus):
        subscription_exists = UserCasinoSubscription.objects.filter(user_id=OuterRef("pk"))
        matching_subscription = UserCasinoSubscription.objects.filter(user_id=OuterRef("pk"), casino=bonus.casino)
        users = list(
            TelegramUser.objects.select_related("settings", "geo")
            .annotate(has_subscription=Exists(subscription_exists), subscribed_to_bonus_casino=Exists(matching_subscription))
            .filter(settings__notify_enabled=True)
            .filter(Q(has_subscription=False) | Q(subscribed_to_bonus_casino=True))
        )
        eligible_users = []
        for user in users:
            if not TelegramBonusService._matches_user_settings(bonus, user.settings):
                continue
            if user.geo_id:
                if not TelegramBonusService._bonus_matches_user_geo(bonus, user):
                    continue
            elif not TelegramBonusService._is_bonus_in_no_geo_selection(user, bonus):
                continue
            eligible_users.append(user)
        return eligible_users

    async def _send_message(self, chat_id, text):
        bot = Bot(settings.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
