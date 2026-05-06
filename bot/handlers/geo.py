from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.keyboards.geo import geo_keyboard, geo_search_prompt_keyboard, geo_search_results_keyboard
from bonus_telegram_bot.bot.utils.global_nav import send_global_navigation_message
from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.services.geo_service import GeoService
from bonus_telegram_bot.services.user_service import TelegramUserService

GEO_SEARCH_STATE_KEY = "geo_search"
GEO_SEARCH_MIN_QUERY_LENGTH = 2


async def send_geo_picker(message, telegram_id, telegram_language_code=None, page_number=0):
    page_data = await GeoService.page(page_number)
    translator = await TelegramI18nService.for_user(telegram_id, telegram_language_code)
    await message.reply_text(
        translator.t("geo.prompt"),
        reply_markup=geo_keyboard(page_data, translator),
    )


async def edit_geo_picker(query, telegram_id, telegram_language_code=None, page_number=0):
    page_data = await GeoService.page(page_number)
    translator = await TelegramI18nService.for_user(telegram_id, telegram_language_code)
    await query.edit_message_text(
        translator.t("geo.prompt"),
        reply_markup=geo_keyboard(page_data, translator),
    )


async def geo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    _clear_geo_search_state(context)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    await send_geo_picker(
        update.effective_message,
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
        page_number=0,
    )
    await send_global_navigation_message(update.effective_message, translator)


async def geo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, action, value = query.data.split(":", 2)
    if action == "page":
        _clear_geo_search_state(context)
        await edit_geo_picker(
            query,
            query.from_user.id,
            getattr(query.from_user, "language_code", None),
            page_number=int(value),
        )
        return
    if action == "search":
        await _activate_geo_search(
            query,
            context,
            page_number=int(value),
        )
        return
    if action == "back":
        _clear_geo_search_state(context)
        await edit_geo_picker(
            query,
            query.from_user.id,
            getattr(query.from_user, "language_code", None),
            page_number=int(value),
        )
        return
    if action == "set":
        _clear_geo_search_state(context)
        user = await TelegramUserService.set_geo(query.from_user.id, value)
        translator = await TelegramI18nService.for_user(
            query.from_user.id,
            getattr(query.from_user, "language_code", None),
        )
        await query.edit_message_text(
            translator.t(
                "geo.updated",
                geo_name=user.geo.name,
                geo_code=user.geo.code.upper(),
            )
        )


async def geo_search_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = _pop_geo_search_state(context)
    if not state:
        return

    message = update.effective_message
    text = ((message.text if message else "") or "").strip()
    if not message or not text:
        return

    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )

    if len(text) < GEO_SEARCH_MIN_QUERY_LENGTH:
        await _edit_geo_search_results(
            context,
            state,
            translator.t("geo.search.too_short", min_chars=GEO_SEARCH_MIN_QUERY_LENGTH),
            [],
        )
        return

    matches = await GeoService.search(text, limit=GeoService.SEARCH_LIMIT)
    if not matches:
        await _edit_geo_search_results(
            context,
            state,
            translator.t("geo.search.no_results", query=text),
            [],
        )
        return

    await _edit_geo_search_results(
        context,
        state,
        translator.t("geo.search.results", query=text),
        matches,
    )


async def _activate_geo_search(query, context, page_number):
    if not query.message:
        return
    translator = await TelegramI18nService.for_user(
        query.from_user.id,
        getattr(query.from_user, "language_code", None),
    )
    _set_geo_search_state(
        context,
        chat_id=getattr(query.message, "chat_id", None),
        message_id=getattr(query.message, "message_id", None),
        back_page=page_number,
        user_id=query.from_user.id,
        language_code=getattr(query.from_user, "language_code", None),
    )
    await query.edit_message_text(
        translator.t("geo.search.prompt"),
        reply_markup=geo_search_prompt_keyboard(translator, page_number),
    )


async def _edit_geo_search_results(context, state, text, matches):
    if not state.get("chat_id") or not state.get("message_id"):
        return
    translator = await TelegramI18nService.for_user(
        state["user_id"],
        state.get("language_code"),
    )
    await context.bot.edit_message_text(
        chat_id=state["chat_id"],
        message_id=state["message_id"],
        text=text,
        reply_markup=geo_search_results_keyboard(matches, translator, state["back_page"]),
    )


def _set_geo_search_state(context, chat_id, message_id, back_page, user_id, language_code=None):
    context.user_data[GEO_SEARCH_STATE_KEY] = {
        "active": True,
        "chat_id": chat_id,
        "message_id": message_id,
        "back_page": back_page,
        "user_id": user_id,
        "language_code": language_code,
    }


def _pop_geo_search_state(context):
    state = context.user_data.pop(GEO_SEARCH_STATE_KEY, None)
    if not state or not state.get("active"):
        return None
    return state


def _clear_geo_search_state(context):
    context.user_data.pop(GEO_SEARCH_STATE_KEY, None)
