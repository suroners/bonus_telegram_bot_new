import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bonus_telegram_bot.bot.handlers import geo as geo_handler
from bonus_telegram_bot.i18n import TelegramI18nService


def test_geo_keyboard_includes_search_button():
    keyboard = geo_handler.geo_keyboard(
        {"page": 1, "has_prev": True, "has_next": True, "geos": [], "total": 0},
        TelegramI18nService.translator(preferred_language="en"),
    )

    assert keyboard.inline_keyboard[0][0].text == "🔎 Search GEO"
    assert keyboard.inline_keyboard[0][0].callback_data == "geo:search:1"


@pytest.mark.django_db
def test_geo_callback_search_activates_one_shot_search(monkeypatch):
    translator = TelegramI18nService.translator(preferred_language="en")
    query = SimpleNamespace(
        data="geo:search:2",
        from_user=SimpleNamespace(id=11, language_code="en"),
        message=SimpleNamespace(chat_id=501, message_id=9001),
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    monkeypatch.setattr(geo_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))

    asyncio.run(geo_handler.geo_callback(update, context))

    assert context.user_data[geo_handler.GEO_SEARCH_STATE_KEY] == {
        "active": True,
        "chat_id": 501,
        "message_id": 9001,
        "back_page": 2,
        "user_id": 11,
        "language_code": "en",
    }
    args, kwargs = query.edit_message_text.await_args
    assert args[0] == "🔎 Type a country name or GEO code."
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "geo:back:2"


def test_geo_search_message_ignores_plain_text_without_active_state(monkeypatch):
    register_mock = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=15, language_code="en"),
        effective_message=SimpleNamespace(text="uk"),
    )
    context = SimpleNamespace(
        user_data={},
        bot=SimpleNamespace(edit_message_text=AsyncMock()),
    )

    monkeypatch.setattr(geo_handler.TelegramUserService, "register", register_mock)

    asyncio.run(geo_handler.geo_search_message(update, context))

    register_mock.assert_not_awaited()
    context.bot.edit_message_text.assert_not_awaited()


@pytest.mark.django_db
def test_geo_search_message_too_short_clears_state_and_shows_retry(monkeypatch):
    translator = TelegramI18nService.translator(preferred_language="en")
    register_mock = AsyncMock()
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=16, language_code="en"),
        effective_message=SimpleNamespace(text="u"),
    )
    context = SimpleNamespace(
        user_data={
            geo_handler.GEO_SEARCH_STATE_KEY: {
                "active": True,
                "chat_id": 77,
                "message_id": 88,
                "back_page": 1,
                "user_id": 16,
                "language_code": "en",
            }
        },
        bot=SimpleNamespace(edit_message_text=AsyncMock()),
    )

    monkeypatch.setattr(geo_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(geo_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))

    asyncio.run(geo_handler.geo_search_message(update, context))

    assert geo_handler.GEO_SEARCH_STATE_KEY not in context.user_data
    args, kwargs = context.bot.edit_message_text.await_args
    assert kwargs["chat_id"] == 77
    assert kwargs["message_id"] == 88
    assert kwargs["text"] == "🔎 Type at least 2 characters."
    assert kwargs["reply_markup"].inline_keyboard[-1][0].callback_data == "geo:search:1"
    assert kwargs["reply_markup"].inline_keyboard[-1][1].callback_data == "geo:back:1"


@pytest.mark.django_db
def test_geo_search_message_shows_matches_and_clears_state(monkeypatch):
    translator = TelegramI18nService.translator(preferred_language="en")
    register_mock = AsyncMock()
    search_mock = AsyncMock(
        return_value=[
            {"code": "uk", "name": "United Kingdom", "parent__code": None},
            {"code": "ua", "name": "Ukraine", "parent__code": None},
        ]
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=17, language_code="en"),
        effective_message=SimpleNamespace(text="uk"),
    )
    context = SimpleNamespace(
        user_data={
            geo_handler.GEO_SEARCH_STATE_KEY: {
                "active": True,
                "chat_id": 90,
                "message_id": 91,
                "back_page": 0,
                "user_id": 17,
                "language_code": "en",
            }
        },
        bot=SimpleNamespace(edit_message_text=AsyncMock()),
    )

    monkeypatch.setattr(geo_handler.TelegramUserService, "register", register_mock)
    monkeypatch.setattr(geo_handler.TelegramI18nService, "for_user", AsyncMock(return_value=translator))
    monkeypatch.setattr(geo_handler.GeoService, "search", search_mock)

    asyncio.run(geo_handler.geo_search_message(update, context))

    search_mock.assert_awaited_once_with("uk", limit=geo_handler.GeoService.SEARCH_LIMIT)
    assert geo_handler.GEO_SEARCH_STATE_KEY not in context.user_data
    args, kwargs = context.bot.edit_message_text.await_args
    assert kwargs["text"] == "🔎 Search results for: uk"
    first_row = kwargs["reply_markup"].inline_keyboard[0]
    assert [button.callback_data for button in first_row] == ["geo:set:uk", "geo:set:ua"]


def test_geo_callback_back_clears_search_state_and_restores_page(monkeypatch):
    query = SimpleNamespace(
        data="geo:back:3",
        from_user=SimpleNamespace(id=18, language_code="en"),
        answer=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={geo_handler.GEO_SEARCH_STATE_KEY: {"active": True}})
    edit_geo_picker = AsyncMock()

    monkeypatch.setattr(geo_handler, "edit_geo_picker", edit_geo_picker)

    asyncio.run(geo_handler.geo_callback(update, context))

    assert geo_handler.GEO_SEARCH_STATE_KEY not in context.user_data
    edit_geo_picker.assert_awaited_once_with(query, 18, "en", page_number=3)
