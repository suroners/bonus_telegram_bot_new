import logging

from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram handler failed", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        translator = TelegramI18nService.translator()
        if update.effective_user:
            translator = await TelegramI18nService.for_user(
                update.effective_user.id,
                getattr(update.effective_user, "language_code", None),
            )
        await update.effective_message.reply_text(
            translator.t("common.error.generic"),
            reply_markup=global_navigation_keyboard(translator),
        )
