from django.conf import settings
from django.core.management.base import BaseCommand

from bonus_scraping.services.proxy_service import PublicProxyListClient, PublicProxyListSync


class Command(BaseCommand):
    help = "Sync a no-auth public proxy list into ScraperProxy rows for testing."

    def add_arguments(self, parser):
        parser.add_argument("--url", default="", help="Plain-text proxy list URL. Defaults to PUBLIC_PROXY_LIST_URL.")
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum proxies to import. Defaults to PUBLIC_PROXY_IMPORT_LIMIT.",
        )
        parser.add_argument(
            "--keep-missing",
            action="store_true",
            help="Keep previously imported public proxies active even if missing from the latest source response.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is None:
            limit = settings.PUBLIC_PROXY_IMPORT_LIMIT
        client = PublicProxyListClient(source_url=options["url"] or settings.PUBLIC_PROXY_LIST_URL)
        result = PublicProxyListSync(client=client).sync(
            limit=limit,
            deactivate_missing=not options["keep_missing"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Synced public proxies: created=%(created)s updated=%(updated)s "
                "skipped=%(skipped)s deactivated=%(deactivated)s" % result
            )
        )
