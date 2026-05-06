from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.handlers.bonuses import send_bonus_cards
from bonus_telegram_bot.bot.handlers.geo import edit_geo_picker
from bonus_telegram_bot.bot.handlers.settings import send_settings_message
from bonus_telegram_bot.bot.keyboards.start import start_keyboard
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard, send_global_navigation_message
from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.services.user_service import TelegramUserService


async def send_start_message(message, telegram_user):
    translator = await TelegramI18nService.for_user(
        telegram_user.id,
        getattr(telegram_user, "language_code", None),
    )
    await message.reply_text(
        translator.t("start.welcome"),
        reply_markup=start_keyboard(translator),
    )
    return translator


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await send_start_message(update.effective_message, update.effective_user)
    await send_global_navigation_message(update.effective_message, translator)


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await TelegramUserService.register(query.from_user)
    translator = await TelegramI18nService.for_user(
        query.from_user.id,
        getattr(query.from_user, "language_code", None),
    )
    _, action = query.data.split(":", 1)

    if action == "geo":
        await edit_geo_picker(
            query,
            query.from_user.id,
            getattr(query.from_user, "language_code", None),
            page_number=0,
        )
        return
    if action == "bonuses" and query.message:
        await send_bonus_cards(
            query.message,
            query.from_user.id,
            getattr(query.from_user, "language_code", None),
        )
        return
    if action == "settings" and query.message:
        await send_settings_message(query.message, query.from_user)
        return
    if action == "subscribe" and query.message:
        await query.message.reply_text(
            translator.t("start.subscribe_help"),
            reply_markup=global_navigation_keyboard(translator),
        )
