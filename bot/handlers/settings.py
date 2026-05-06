from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.keyboards.settings import currency_keyboard, language_keyboard, settings_keyboard
from bonus_telegram_bot.bot.utils.formatting import settings_text
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard, send_global_navigation_message
from bonus_telegram_bot.i18n import TelegramI18nService, normalize_locale
from bonus_telegram_bot.services.settings_service import TelegramSettingsService
from bonus_telegram_bot.services.user_service import TelegramUserService


async def send_settings_message(message, telegram_user):
    snapshot = await TelegramSettingsService.snapshot(telegram_user.id)
    translator = _translator_from_snapshot(snapshot, getattr(telegram_user, "language_code", None))
    await message.reply_text(
        settings_text(snapshot, translator),
        reply_markup=settings_keyboard(snapshot, translator),
    )
    return translator


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await send_settings_message(update.effective_message, update.effective_user)
    await send_global_navigation_message(update.effective_message, translator)


async def currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    value = " ".join(context.args).strip()
    if not value:
        await update.effective_message.reply_text(
            translator.t("settings.command.currency_usage"),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    snapshot = await TelegramSettingsService.set_currency(update.effective_user.id, value)
    translator = _translator_from_snapshot(snapshot, getattr(update.effective_user, "language_code", None))
    await update.effective_message.reply_text(
        settings_text(snapshot, translator),
        reply_markup=settings_keyboard(snapshot, translator),
    )
    await send_global_navigation_message(update.effective_message, translator)


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    value = " ".join(context.args).strip()
    if not value:
        await update.effective_message.reply_text(
            translator.t("settings.command.language_usage"),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    snapshot = await TelegramSettingsService.set_language(update.effective_user.id, value)
    translator = _translator_from_snapshot(snapshot, getattr(update.effective_user, "language_code", None))
    await update.effective_message.reply_text(
        settings_text(snapshot, translator),
        reply_markup=settings_keyboard(snapshot, translator),
    )
    await send_global_navigation_message(update.effective_message, translator)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 2)
    if len(parts) < 2:
        return
    action = parts[1]
    if action == "toggle" and len(parts) == 3:
        snapshot = await TelegramSettingsService.toggle(query.from_user.id, parts[2])
        await _edit_settings_screen(query, query.from_user, snapshot)
        return
    if action == "language":
        await _edit_language_picker(query, query.from_user)
        return
    if action == "currency":
        await _edit_currency_picker(query, query.from_user)
        return
    if action == "set_language" and len(parts) == 3:
        snapshot = await TelegramSettingsService.set_language(query.from_user.id, parts[2])
        await _edit_settings_screen(query, query.from_user, snapshot)
        translator = _translator_from_snapshot(snapshot, getattr(query.from_user, "language_code", None))
        if getattr(query, "message", None):
            await send_global_navigation_message(query.message, translator)
        return
    if action == "set_currency" and len(parts) == 3:
        snapshot = await TelegramSettingsService.set_currency(query.from_user.id, parts[2])
        await _edit_settings_screen(query, query.from_user, snapshot)
        return
    if action == "back":
        snapshot = await TelegramSettingsService.snapshot(query.from_user.id)
        await _edit_settings_screen(query, query.from_user, snapshot)


def _translator_from_snapshot(snapshot, telegram_language_code=None):
    return TelegramI18nService.translator(
        preferred_language=snapshot["preferred_language"],
        telegram_language_code=telegram_language_code,
    )


async def _edit_settings_screen(query, telegram_user, snapshot):
    translator = _translator_from_snapshot(snapshot, getattr(telegram_user, "language_code", None))
    await query.edit_message_text(
        settings_text(snapshot, translator),
        reply_markup=settings_keyboard(snapshot, translator),
    )
    return translator


async def _edit_language_picker(query, telegram_user):
    snapshot = await TelegramSettingsService.snapshot(telegram_user.id)
    translator = _translator_from_snapshot(snapshot, getattr(telegram_user, "language_code", None))
    current_language = normalize_locale(snapshot["preferred_language"]) or translator.locale
    await query.edit_message_text(
        translator.t("settings.picker.language_title"),
        reply_markup=language_keyboard(translator, current_language),
    )


async def _edit_currency_picker(query, telegram_user):
    snapshot = await TelegramSettingsService.snapshot(telegram_user.id)
    translator = _translator_from_snapshot(snapshot, getattr(telegram_user, "language_code", None))
    await query.edit_message_text(
        translator.t("settings.picker.currency_title"),
        reply_markup=currency_keyboard(translator, snapshot["preferred_currency"]),
    )
