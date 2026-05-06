from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.utils.formatting import format_bonus_cards
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard
from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.services.bonus_service import TelegramBonusService
from bonus_telegram_bot.services.user_service import TelegramUserService


async def casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    casino_name = " ".join(context.args).strip()
    if not casino_name:
        await update.effective_message.reply_text(
            translator.t("casino.usage"),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    result = await TelegramBonusService.casino_bonus_cards(update.effective_user.id, casino_name, limit=10)
    if not result["found"]:
        similar = ", ".join(result["similar"]) or translator.t("casino.no_similar")
        await update.effective_message.reply_text(
            translator.t("casino.not_found", similar=similar),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    await update.effective_message.reply_text(
        format_bonus_cards(result["bonuses"], translator),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=global_navigation_keyboard(translator),
    )
