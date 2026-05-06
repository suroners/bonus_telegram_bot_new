from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bonus_scraping.services.webshare_service import WebshareProxyClient, WebshareProxySync


class Command(BaseCommand):
    help = "Sync Webshare proxy list into ScraperProxy rows."

    def add_arguments(self, parser):
        parser.add_argument("--token", default="", help="Webshare API token. Defaults to WEBSHARE_API_TOKEN.")
        parser.add_argument("--mode", default="", help="Webshare proxy mode. Defaults to WEBSHARE_PROXY_MODE.")
        parser.add_argument(
            "--country-codes",
            default="",
            help="Comma-separated country codes like US,GB,FR. Defaults to WEBSHARE_COUNTRY_CODES.",
        )
        parser.add_argument("--include-invalid", action="store_true", help="Import proxies marked invalid by Webshare.")
        parser.add_argument(
            "--keep-missing",
            action="store_true",
            help="Keep previously imported Webshare proxies active even if they are missing from the latest API response.",
        )

    def handle(self, *args, **options):
        token = options["token"] or settings.WEBSHARE_API_TOKEN
        if not token:
            raise CommandError("Set WEBSHARE_API_TOKEN or pass --token to sync Webshare proxies.")

        mode = options["mode"] or settings.WEBSHARE_PROXY_MODE
        country_codes = self._country_codes(options["country_codes"])
        client = WebshareProxyClient(token=token, mode=mode)
        result = WebshareProxySync(client=client).sync(
            country_codes=country_codes,
            include_invalid=options["include_invalid"],
            deactivate_missing=not options["keep_missing"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Synced Webshare proxies: created=%(created)s updated=%(updated)s "
                "skipped=%(skipped)s deactivated=%(deactivated)s" % result
            )
        )

    @staticmethod
    def _country_codes(value):
        if value:
            return [item.strip().upper() for item in value.split(",") if item.strip()]
        return settings.WEBSHARE_COUNTRY_CODES
