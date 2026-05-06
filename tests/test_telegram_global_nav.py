import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram import ReplyKeyboardMarkup

from bonus_telegram_bot.bot.handlers import text as text_handler
from bonus_telegram_bot.bot.handlers.bonuses import send_bonus_cards
from bonus_telegram_bot.bot.utils.global_nav import (
    global_navigation_action,
    global_navigation_keyboard,
)
from bonus_telegram_bot.i18n import TelegramI18nService


def test_global_navigation_keyboard_is_localized_and_persistent():
    keyboard_en = global_navigation_keyboard(TelegramI18nService.translator(preferred_language="en"))
    keyboard_ru = global_navigation_keyboard(TelegramI18nService.translator(preferred_language="ru"))

    assert isinstance(keyboard_en, ReplyKeyboardMarkup)
    assert keyboard_en.is_persistent is True
    assert keyboard_en.resize_keyboard is True
    assert [[button.text for button in row] for row in keyboard_en.keyboard] == [
        ["🏠 Home", "🎁 Bonuses"],
        ["🌍 GEO", "⚙️ Settings"],
    ]
    assert [[button.text for button in row] for row in keyboard_ru.keyboard] == [
        ["🏠 Главная", "🎁 Бонусы"],
        ["🌍 GEO", "⚙️ Настройки"],
    ]


def test_global_navigation_action_matches_all_supported_locales():
    assert global_navigation_action("🏠 Home") == "home"
    assert global_navigation_action("🎁 Бонусы") == "bonuses"
    assert global_navigation_action("🌍 GEO") == "geo"
    assert global_navigation_action("⚙️ Настройки") == "settings"
    assert global_navigation_action("unknown") is None


@pytest.mark.django_db
def test_text_router_global_button_takes_precedence_over_geo_search(monkeypatch):
    register_mock = AsyncMock()
    send_start_message = AsyncMock()
    geo_search_message = AsyncMock()
    clear_state = {}
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=41, language_code="en"),
        effective_message=SimpleNamespace(text="🏠 Home"),
    )
    context = SimpleNamespace(user_data={"geo_search": {"active": True}})

    monkeypatch.setattr(text_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(text_handler, "send_start_message", send_start_message)
    monkeypatch.setattr(text_handler, "geo_search_message", geo_search_message)

    asyncio.run(text_handler.text_message_router(update, context))

    register_mock.assert_awaited_once_with(update.effective_user)
    send_start_message.assert_awaited_once_with(update.effective_message, update.effective_user)
    geo_search_message.assert_not_awaited()
    assert context.user_data == clear_state


def test_text_router_falls_back_to_geo_search(monkeypatch):
    geo_search_message = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42, language_code="en"),
        effective_message=SimpleNamespace(text="not a button"),
    )
    context = SimpleNamespace(user_data={})

    monkeypatch.setattr(text_handler, "geo_search_message", geo_search_message)

    asyncio.run(text_handler.text_message_router(update, context))

    geo_search_message.assert_awaited_once_with(update, context)


@pytest.mark.django_db
def test_send_bonus_cards_attaches_persistent_reply_keyboard(monkeypatch):
    translator = TelegramI18nService.translator(preferred_language="en")
    reply_text = AsyncMock()
    message = SimpleNamespace(reply_text=reply_text)

    monkeypatch.setattr(send_bonus_cards.__globals__["TelegramBonusService"], "top_bonus_cards", AsyncMock(return_value=[]))
    monkeypatch.setattr(send_bonus_cards.__globals__["TelegramI18nService"], "for_user", AsyncMock(return_value=translator))

    asyncio.run(send_bonus_cards(message, 77, "en"))

    args, kwargs = reply_text.await_args
    assert args[0].startswith("🎁 No approved bonuses")
    assert isinstance(kwargs["reply_markup"], ReplyKeyboardMarkup)
