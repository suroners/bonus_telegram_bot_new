from django.core.management.base import BaseCommand

from bonus_scraping.services.scraper_service import ScraperService


class Command(BaseCommand):
    help = "Scrape all active casino promotion pages synchronously."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Ignore the 24-hour duplicate scrape guard.")

    def handle(self, *args, **options):
        histories = ScraperService().scrape_all(force=options["force"])
        self.stdout.write(self.style.SUCCESS("Scraped %s pages" % len(histories)))
