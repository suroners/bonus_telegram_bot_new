import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.bot.handlers import start as start_handler
from bonus_telegram_bot.bot.keyboards.start import start_keyboard


def test_start_keyboard_has_expected_buttons():
    keyboard = start_keyboard(TelegramI18nService.translator(preferred_language="en"))

    assert [[button.text for button in row] for row in keyboard.inline_keyboard] == [
        ["🌍 Set GEO", "🎁 View Bonuses"],
        ["⚙️ Settings", "⭐ Subscribe"],
    ]
    assert [[button.callback_data for button in row] for row in keyboard.inline_keyboard] == [
        ["start:geo", "start:bonuses"],
        ["start:settings", "start:subscribe"],
    ]


@pytest.mark.django_db
def test_start_handler_sends_welcome_message(monkeypatch):
    register_mock = AsyncMock()
    global_nav_mock = AsyncMock()
    reply_text = AsyncMock()
    translator = TelegramI18nService.translator(preferred_language="en")
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, language_code="en"),
        effective_message=SimpleNamespace(reply_text=reply_text),
    )

    monkeypatch.setattr(start_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(start_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))
    monkeypatch.setattr(start_handler, "send_global_navigation_message", global_nav_mock)

    asyncio.run(start_handler.start(update, SimpleNamespace()))

    register_mock.assert_awaited_once_with(update.effective_user)
    reply_text.assert_awaited_once()
    args, kwargs = reply_text.await_args
    assert args[0] == translator.t("start.welcome")
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "start:geo"
    global_nav_mock.assert_awaited_once_with(update.effective_message, translator)


@pytest.mark.django_db
def test_start_callback_geo_edits_message(monkeypatch):
    register_mock = AsyncMock()
    edit_geo_picker = AsyncMock()
    answer = AsyncMock()
    translator = TelegramI18nService.translator(preferred_language="en")
    query = SimpleNamespace(
        data="start:geo",
        from_user=SimpleNamespace(id=2, language_code="en"),
        answer=answer,
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query)

    monkeypatch.setattr(start_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(start_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))
    monkeypatch.setattr(start_handler, "edit_geo_picker", edit_geo_picker)

    asyncio.run(start_handler.start_callback(update, SimpleNamespace()))

    answer.assert_awaited_once()
    register_mock.assert_awaited_once_with(query.from_user)
    edit_geo_picker.assert_awaited_once_with(query, 2, "en", page_number=0)


@pytest.mark.django_db
def test_start_callback_bonuses_sends_bonus_cards(monkeypatch):
    register_mock = AsyncMock()
    send_bonus_cards = AsyncMock()
    translator = TelegramI18nService.translator(preferred_language="en")
    query = SimpleNamespace(
        data="start:bonuses",
        from_user=SimpleNamespace(id=3, language_code="en"),
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query)

    monkeypatch.setattr(start_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(start_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))
    monkeypatch.setattr(start_handler, "send_bonus_cards", send_bonus_cards)

    asyncio.run(start_handler.start_callback(update, SimpleNamespace()))

    send_bonus_cards.assert_awaited_once_with(query.message, 3, "en")


@pytest.mark.django_db
def test_start_callback_settings_sends_settings_message(monkeypatch):
    register_mock = AsyncMock()
    send_settings_message = AsyncMock()
    translator = TelegramI18nService.translator(preferred_language="en")
    query = SimpleNamespace(
        data="start:settings",
        from_user=SimpleNamespace(id=4, language_code="en"),
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )
    update = SimpleNamespace(callback_query=query)

    monkeypatch.setattr(start_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(start_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))
    monkeypatch.setattr(start_handler, "send_settings_message", send_settings_message)

    asyncio.run(start_handler.start_callback(update, SimpleNamespace()))

    send_settings_message.assert_awaited_once_with(query.message, query.from_user)


@pytest.mark.django_db
def test_start_callback_subscribe_sends_help_message(monkeypatch):
    register_mock = AsyncMock()
    reply_text = AsyncMock()
    translator = TelegramI18nService.translator(preferred_language="en")
    query = SimpleNamespace(
        data="start:subscribe",
        from_user=SimpleNamespace(id=5, language_code="en"),
        answer=AsyncMock(),
        message=SimpleNamespace(reply_text=reply_text),
    )
    update = SimpleNamespace(callback_query=query)

    monkeypatch.setattr(start_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(start_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))

    asyncio.run(start_handler.start_callback(update, SimpleNamespace()))

    args, kwargs = reply_text.await_args
    assert args[0] == translator.t("start.subscribe_help")
    assert kwargs["reply_markup"].keyboard[0][0].text == "🏠 Home"
