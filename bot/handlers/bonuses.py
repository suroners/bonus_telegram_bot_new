from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.utils.formatting import format_bonus_cards
from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard
from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.services.bonus_service import TelegramBonusService
from bonus_telegram_bot.services.user_service import TelegramUserService


async def send_bonus_cards(message, telegram_id, telegram_language_code=None):
    cards = await TelegramBonusService.top_bonus_cards(telegram_id, limit=10)
    translator = await TelegramI18nService.for_user(telegram_id, telegram_language_code)
    await message.reply_text(
        format_bonus_cards(cards, translator),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=global_navigation_keyboard(translator),
    )


async def bonuses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    await send_bonus_cards(
        update.effective_message,
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
