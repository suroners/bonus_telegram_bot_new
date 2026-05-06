from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed all startup data required by scraper and Telegram GEO selection."

    def handle(self, *args, **options):
        call_command("seed_geos")
        call_command("seed_casinos")
        self.stdout.write(self.style.SUCCESS("Startup seed complete"))
