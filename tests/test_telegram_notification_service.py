import pytest

from bonus_core.models import Bonus, Casino, Geo, TelegramUser, UserSettings
from bonus_telegram_bot.services.notification_service import TelegramNotificationService


@pytest.mark.django_db
def test_no_geo_user_only_receives_notifications_for_top_priority_casino_bonus(settings):
    settings.TELEGRAM_NO_GEO_MODE = "top_per_casino"
    settings.TELEGRAM_NO_GEO_CASINO_LIMIT = 3
    settings.TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT = 1
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino_a = Casino.objects.create(name="Casino A", priority=30)
    casino_b = Casino.objects.create(name="Casino B", priority=20)
    casino_c = Casino.objects.create(name="Casino C", priority=10)
    casino_d = Casino.objects.create(name="Casino D", priority=0)
    user = TelegramUser.objects.create(telegram_id=2001)
    UserSettings.objects.get_or_create(user=user)
    top_bonus = Bonus.objects.create(casino=casino_a, geo=geo, title="A Top", is_approved=True, priority=5)
    low_bonus_same_casino = Bonus.objects.create(casino=casino_a, geo=geo, title="A Low", is_approved=True, priority=1)
    Bonus.objects.create(casino=casino_b, geo=geo, title="B Top", is_approved=True, priority=4)
    Bonus.objects.create(casino=casino_c, geo=geo, title="C Top", is_approved=True, priority=3)
    low_priority_casino_bonus = Bonus.objects.create(casino=casino_d, geo=geo, title="D Top", is_approved=True, priority=100)
    service = TelegramNotificationService()

    assert [eligible.telegram_id for eligible in service._eligible_users_for_bonus(top_bonus)] == [2001]
    assert service._eligible_users_for_bonus(low_bonus_same_casino) == []
    assert service._eligible_users_for_bonus(low_priority_casino_bonus) == []


@pytest.mark.django_db
def test_daily_digest_includes_no_geo_user_with_top_three_casinos(monkeypatch, settings):
    settings.TELEGRAM_NO_GEO_MODE = "top_per_casino"
    settings.TELEGRAM_NO_GEO_CASINO_LIMIT = 3
    settings.TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT = 1
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino_a = Casino.objects.create(name="Casino A", priority=30)
    casino_b = Casino.objects.create(name="Casino B", priority=20)
    casino_c = Casino.objects.create(name="Casino C", priority=10)
    casino_d = Casino.objects.create(name="Casino D", priority=0)
    user = TelegramUser.objects.create(telegram_id=2002)
    UserSettings.objects.get_or_create(user=user)
    Bonus.objects.create(casino=casino_a, geo=geo, title="A Top", is_approved=True, priority=5)
    Bonus.objects.create(casino=casino_b, geo=geo, title="B Top", is_approved=True, priority=4)
    Bonus.objects.create(casino=casino_c, geo=geo, title="C Top", is_approved=True, priority=3)
    Bonus.objects.create(casino=casino_d, geo=geo, title="D Top", is_approved=True, priority=100)
    sent_messages = []
    settings.TELEGRAM_BOT_TOKEN = "test-token"

    async def fake_send_message(self, chat_id, text):
        sent_messages.append((chat_id, text))

    monkeypatch.setattr(TelegramNotificationService, "_send_message", fake_send_message)

    result = TelegramNotificationService().broadcast_daily_top_bonuses()

    assert result == {"sent": 1}
    assert sent_messages[0][0] == 2002
    assert "A Top" in sent_messages[0][1]
    assert "B Top" in sent_messages[0][1]
    assert "C Top" in sent_messages[0][1]
    assert "D Top" not in sent_messages[0][1]
