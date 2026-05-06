from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.handlers.bonuses import send_bonus_cards
from bonus_telegram_bot.bot.handlers.geo import _clear_geo_search_state, geo_search_message, send_geo_picker
from bonus_telegram_bot.bot.handlers.settings import send_settings_message
from bonus_telegram_bot.bot.handlers.start import send_start_message
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_action
from bonus_telegram_bot.services.user_service import TelegramUserService


async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    telegram_user = update.effective_user
    text = ((message.text if message else "") or "").strip()
    action = global_navigation_action(text)
    if not action:
        await geo_search_message(update, context)
        return

    await TelegramUserService.register(telegram_user)
    _clear_geo_search_state(context)

    if action == "home":
        await send_start_message(message, telegram_user)
        return
    if action == "bonuses":
        await send_bonus_cards(message, telegram_user.id, getattr(telegram_user, "language_code", None))
        return
    if action == "geo":
        await send_geo_picker(
            message,
            telegram_user.id,
            getattr(telegram_user, "language_code", None),
            page_number=0,
        )
        return
    if action == "settings":
        await send_settings_message(message, telegram_user)
