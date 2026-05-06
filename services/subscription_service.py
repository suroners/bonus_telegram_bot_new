from asgiref.sync import sync_to_async

from bonus_core.models import Casino, TelegramUser, UserCasinoSubscription


class SubscriptionService:
    @staticmethod
    async def subscribe(telegram_id, casino_name):
        return await sync_to_async(SubscriptionService._subscribe)(telegram_id, casino_name)

    @staticmethod
    def _subscribe(telegram_id, casino_name):
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        casino = Casino.objects.filter(name__icontains=casino_name).order_by("-priority", "name").first()
        if not casino:
            return {"ok": False, "code": "casino_not_found"}
        UserCasinoSubscription.objects.get_or_create(user=user, casino=casino)
        return {"ok": True, "code": "subscribed", "casino": casino.name}

    @staticmethod
    async def unsubscribe(telegram_id, casino_name):
        return await sync_to_async(SubscriptionService._unsubscribe)(telegram_id, casino_name)

    @staticmethod
    def _unsubscribe(telegram_id, casino_name):
        user = TelegramUser.objects.get(telegram_id=telegram_id)
        casino = Casino.objects.filter(name__icontains=casino_name).order_by("-priority", "name").first()
        if not casino:
            return {"ok": False, "code": "casino_not_found"}
        deleted, _ = UserCasinoSubscription.objects.filter(user=user, casino=casino).delete()
        if deleted:
            return {"ok": True, "code": "unsubscribed", "casino": casino.name}
        return {"ok": True, "code": "not_subscribed", "casino": casino.name}
