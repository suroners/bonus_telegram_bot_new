import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bonus_core.models import TelegramUser
from bonus_telegram_bot.bot.handlers import settings as settings_handler


pytestmark = pytest.mark.django_db(transaction=True)


def test_send_settings_message_uses_localized_text_and_buttons():
    user = TelegramUser.objects.create(telegram_id=3001)
    user.settings.preferred_language = "ru"
    user.settings.preferred_currency = "usd"
    user.settings.save(update_fields=["preferred_language", "preferred_currency", "updated_at"])
    message = SimpleNamespace(reply_text=AsyncMock())
    telegram_user = SimpleNamespace(id=3001, language_code="ru")

    asyncio.run(settings_handler.send_settings_message(message, telegram_user))

    args, kwargs = message.reply_text.await_args
    assert "⚙️ Настройки" in args[0]
    assert "🌐 Язык: Русский" in args[0]
    assert "💱 Валюта: USD" in args[0]
    assert [button.text for button in kwargs["reply_markup"].inline_keyboard[0]] == ["🌐 Язык", "💱 Валюта"]


def test_settings_callback_shows_language_picker():
    user = TelegramUser.objects.create(telegram_id=3002)
    user.settings.preferred_language = "ru"
    user.settings.save(update_fields=["preferred_language", "updated_at"])
    query = SimpleNamespace(
        data="settings:language",
        from_user=SimpleNamespace(id=3002, language_code="ru"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)

    asyncio.run(settings_handler.settings_callback(update, SimpleNamespace()))

    args, kwargs = query.edit_message_text.await_args
    assert args[0] == "🌐 Выберите язык"
    labels = [row[0].text for row in kwargs["reply_markup"].inline_keyboard]
    assert "✓ Русский" in labels
    assert "English" in labels
    assert labels[-1] == "⬅️ Назад"


def test_settings_callback_sets_language_and_renders_localized_screen():
    user = TelegramUser.objects.create(telegram_id=3003)
    user.settings.preferred_language = "en"
    user.settings.save(update_fields=["preferred_language", "updated_at"])
    query = SimpleNamespace(
        data="settings:set_language:ru",
        from_user=SimpleNamespace(id=3003, language_code="en"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)

    asyncio.run(settings_handler.settings_callback(update, SimpleNamespace()))

    user.refresh_from_db()
    assert user.settings.preferred_language == "ru"
    args, kwargs = query.edit_message_text.await_args
    assert args[0].startswith("⚙️ Настройки")
    assert kwargs["reply_markup"].inline_keyboard[0][0].text == "🌐 Язык"


def test_settings_callback_shows_currency_picker():
    user = TelegramUser.objects.create(telegram_id=3004)
    user.settings.preferred_language = "en"
    user.settings.preferred_currency = "GBP"
    user.settings.save(update_fields=["preferred_language", "preferred_currency", "updated_at"])
    query = SimpleNamespace(
        data="settings:currency",
        from_user=SimpleNamespace(id=3004, language_code="en"),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)

    asyncio.run(settings_handler.settings_callback(update, SimpleNamespace()))

    args, kwargs = query.edit_message_text.await_args
    assert args[0] == "💱 Choose currency"
    labels = [row[0].text for row in kwargs["reply_markup"].inline_keyboard]
    assert "✓ GBP" in labels
    assert "USD" in labels
    assert labels[-1] == "⬅️ Back"


def test_language_command_without_value_returns_localized_usage(monkeypatch):
    user = TelegramUser.objects.create(telegram_id=3005)
    user.settings.preferred_language = "ru"
    user.settings.save(update_fields=["preferred_language", "updated_at"])
    register_mock = AsyncMock()
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=3005, language_code="ru"),
        effective_message=message,
    )
    context = SimpleNamespace(args=[])

    monkeypatch.setattr(settings_handler.TelegramUserService, "register", register_mock)

    asyncio.run(settings_handler.language(update, context))

    args, kwargs = message.reply_text.await_args
    assert args[0] == "Используйте /language en или /language ru."
    assert kwargs["reply_markup"].keyboard[0][0].text == "🏠 Главная"


def test_currency_command_updates_settings_screen_in_english(monkeypatch):
    user = TelegramUser.objects.create(telegram_id=3006)
    user.settings.preferred_language = "en"
    user.settings.save(update_fields=["preferred_language", "updated_at"])
    register_mock = AsyncMock()
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=3006, language_code="en"),
        effective_message=message,
    )
    context = SimpleNamespace(args=["gbp"])
    send_global_navigation_message = AsyncMock()

    monkeypatch.setattr(settings_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(settings_handler, "send_global_navigation_message", send_global_navigation_message)

    asyncio.run(settings_handler.currency(update, context))

    user.refresh_from_db()
    assert user.settings.preferred_currency == "GBP"
    args, kwargs = message.reply_text.await_args
    assert args[0].startswith("⚙️ Settings")
    assert "💱 Currency: GBP" in args[0]
    assert kwargs["reply_markup"].inline_keyboard[0][1].text == "💱 Currency"
    send_global_navigation_message.assert_awaited_once()
