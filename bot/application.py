from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bonus_telegram_bot.bot.handlers.bonuses import bonuses
from bonus_telegram_bot.bot.handlers.casino import casino
from bonus_telegram_bot.bot.handlers.errors import error_handler
from bonus_telegram_bot.bot.handlers.geo import geo, geo_callback
from bonus_telegram_bot.bot.handlers.settings import currency, language
from bonus_telegram_bot.bot.handlers.settings import settings as settings_handler
from bonus_telegram_bot.bot.handlers.settings import settings_callback
from bonus_telegram_bot.bot.handlers.start import start, start_callback
from bonus_telegram_bot.bot.handlers.subscriptions import subscribe, unsubscribe
from bonus_telegram_bot.bot.handlers.text import text_message_router


def build_application():
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("geo", geo))
    application.add_handler(CommandHandler("settings", settings_handler))
    application.add_handler(CommandHandler("currency", currency))
    application.add_handler(CommandHandler("language", language))
    application.add_handler(CommandHandler("bonuses", bonuses))
    application.add_handler(CommandHandler("casino", casino))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CallbackQueryHandler(start_callback, pattern=r"^start:"))
    application.add_handler(CallbackQueryHandler(geo_callback, pattern=r"^geo:"))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))
    application.add_error_handler(error_handler)
    return application
