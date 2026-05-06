from django.core.management.base import BaseCommand
from telegram import Update

from bonus_telegram_bot.bot.application import build_application


class Command(BaseCommand):
    help = "Run the Telegram bot polling loop."

    def handle(self, *args, **options):
        application = build_application()
        self.stdout.write(self.style.SUCCESS("Starting Telegram bot polling"))
        application.run_polling(allowed_updates=Update.ALL_TYPES)
