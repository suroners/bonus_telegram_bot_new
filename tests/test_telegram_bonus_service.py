from types import SimpleNamespace

import pytest

from bonus_core.models import Bonus, Casino, Geo, TelegramUser, UserSettings
from bonus_telegram_bot.services.bonus_service import TelegramBonusService
from bonus_telegram_bot.services.user_service import TelegramUserService


@pytest.mark.django_db
def test_top_bonus_cards_rank_bonus_priority_then_casino_priority():
    geo = Geo.objects.create(code="ca", name="Canada")
    low_casino = Casino.objects.create(name="Low Casino", priority=0)
    high_casino = Casino.objects.create(name="High Casino", priority=10)
    user = TelegramUser.objects.create(telegram_id=123, geo=geo)
    UserSettings.objects.get_or_create(user=user)
    Bonus.objects.create(casino=low_casino, geo=geo, title="Low", is_approved=True, priority=1)
    Bonus.objects.create(casino=high_casino, geo=geo, title="High", is_approved=True, priority=1)
    Bonus.objects.create(casino=low_casino, geo=geo, title="Top", is_approved=True, priority=5)

    cards = TelegramBonusService._top_bonus_cards(123, limit=3)

    assert [card["title"] for card in cards] == ["Top", "High", "Low"]


@pytest.mark.django_db
def test_child_geo_user_sees_parent_geo_bonus():
    country = Geo.objects.create(code="us", name="USA")
    state = Geo.objects.create(code="us-ny", name="New York", parent=country)
    casino = Casino.objects.create(name="Parent Geo Casino")
    user = TelegramUser.objects.create(telegram_id=456, geo=state)
    UserSettings.objects.get_or_create(user=user)
    Bonus.objects.create(casino=casino, geo=country, title="US Bonus", is_approved=True)

    cards = TelegramBonusService._top_bonus_cards(456, limit=3)

    assert [card["title"] for card in cards] == ["US Bonus"]


@pytest.mark.django_db
def test_no_geo_top_bonus_cards_use_top_casino_priority_and_one_bonus_per_casino(settings):
    settings.TELEGRAM_NO_GEO_MODE = "top_per_casino"
    settings.TELEGRAM_NO_GEO_CASINO_LIMIT = 3
    settings.TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT = 1
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino_a = Casino.objects.create(name="Casino A", priority=30)
    casino_b = Casino.objects.create(name="Casino B", priority=20)
    casino_c = Casino.objects.create(name="Casino C", priority=10)
    casino_d = Casino.objects.create(name="Casino D", priority=0)
    user = TelegramUser.objects.create(telegram_id=789)
    UserSettings.objects.get_or_create(user=user)
    Bonus.objects.create(casino=casino_a, geo=geo, title="A Low", is_approved=True, priority=1)
    Bonus.objects.create(casino=casino_a, geo=geo, title="A Top", is_approved=True, priority=5)
    Bonus.objects.create(casino=casino_b, geo=geo, title="B Top", is_approved=True, priority=1)
    Bonus.objects.create(casino=casino_c, geo=geo, title="C Top", is_approved=True, priority=1)
    Bonus.objects.create(casino=casino_d, geo=geo, title="D Top", is_approved=True, priority=100)

    cards = TelegramBonusService._top_bonus_cards(789, limit=10)

    assert [card["title"] for card in cards] == ["A Top", "B Top", "C Top"]


@pytest.mark.django_db
def test_no_geo_casino_bonus_cards_return_up_to_three_for_selected_casino(settings):
    settings.TELEGRAM_NO_GEO_CASINO_COMMAND_LIMIT = 3
    geo = Geo.objects.create(code="fr", name="France")
    casino = Casino.objects.create(name="Focused Casino", priority=20)
    user = TelegramUser.objects.create(telegram_id=790)
    UserSettings.objects.get_or_create(user=user)
    Bonus.objects.create(casino=casino, geo=geo, title="Third", is_approved=True, priority=1)
    Bonus.objects.create(casino=casino, geo=geo, title="First", is_approved=True, priority=5)
    Bonus.objects.create(casino=casino, geo=geo, title="Second", is_approved=True, priority=3)
    Bonus.objects.create(casino=casino, geo=geo, title="Fourth", is_approved=True, priority=0)

    result = TelegramBonusService._casino_bonus_cards(790, "Focused", limit=10)

    assert result["found"] is True
    assert [card["title"] for card in result["bonuses"]] == ["First", "Second", "Third"]


@pytest.mark.django_db
def test_register_infers_geo_from_language_region():
    Geo.objects.create(code="uk", name="United Kingdom")

    user = TelegramUserService._register(
        SimpleNamespace(
            id=1001,
            username="region-user",
            first_name="Region",
            last_name="User",
            language_code="en-GB",
        )
    )

    user.refresh_from_db()
    assert user.geo.code == "uk"
    assert user.settings.preferred_language == "en-gb"


@pytest.mark.django_db
def test_register_uses_language_fallback_and_preserves_existing_geo():
    fallback_geo = Geo.objects.create(code="fr", name="France")
    manual_geo = Geo.objects.create(code="nl", name="Netherlands")
    TelegramUserService._register(
        SimpleNamespace(
            id=1002,
            username="fallback-user",
            first_name="Fallback",
            last_name="User",
            language_code="fr",
        )
    )
    existing = TelegramUser.objects.create(telegram_id=1003, geo=manual_geo)
    UserSettings.objects.get_or_create(user=existing)

    TelegramUserService._register(
        SimpleNamespace(
            id=1003,
            username="manual-user",
            first_name="Manual",
            last_name="Geo",
            language_code="en-gb",
        )
    )

    inferred = TelegramUser.objects.get(telegram_id=1002)
    existing.refresh_from_db()
    assert inferred.geo == fallback_geo
    assert existing.geo == manual_geo
