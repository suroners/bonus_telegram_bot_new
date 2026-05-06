import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from bonus_core.models import Casino, CasinoBonusPage, CasinoLocation, Geo, Vertical
from bonus_core.services.geo_normalizer import normalize_geo_code


class Command(BaseCommand):
    help = "Seed casinos and promotion URLs from grouped_casinos_with_verticals_10.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR / "bonus_scraping" / "grouped_casinos_with_verticals_10.json"),
            help="Path to grouped casino JSON",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise FileNotFoundError("Casino seed file not found: %s" % path)

        with path.open("r", encoding="utf-8") as file_handle:
            rows = json.load(file_handle)

        for row in rows:
            casino = self._upsert_casino(row)
            self._upsert_verticals(casino, row.get("verticals") or [])
            self._upsert_locations(casino, row.get("locations") or [])
            self._upsert_promotion_urls(casino, row.get("promotions") or {})

        self.stdout.write(self.style.SUCCESS("Seeded %s casinos" % Casino.objects.count()))

    def _upsert_casino(self, row):
        casino, _ = Casino.objects.update_or_create(
            source_id=row.get("brand_id"),
            defaults={
                "name": row.get("brand_name") or "Unknown casino",
                "slug": row.get("brand_slug") or "",
                "regulated_option": row.get("regulated_option") or "",
                "crypto_friendly_option": row.get("crypto_friendly_option") or "",
                "my_brand": bool(row.get("my_brand")),
            },
        )
        return casino

    def _upsert_verticals(self, casino, rows):
        verticals = []
        for row in rows:
            vertical, _ = Vertical.objects.update_or_create(
                source_id=row.get("id"),
                defaults={"name": row.get("name") or "Unknown"},
            )
            verticals.append(vertical)
        casino.verticals.set(verticals)

    def _upsert_locations(self, casino, rows):
        for row in rows:
            source_code = row.get("geo_code")
            code = normalize_geo_code(source_code)
            geo = Geo.objects.filter(code=code).first()
            if not geo:
                self.stderr.write("Skipping unknown GEO location code %s for %s" % (source_code, casino))
                continue
            CasinoLocation.objects.update_or_create(
                casino=casino,
                geo=geo,
                defaults={
                    "brand_traffic_share": row.get("brand_traffic_share") or 0,
                    "location_id": row.get("location_id"),
                    "total_share_of_traffic": row.get("total_share_of_traffic") or 0,
                    "market_share": self._decimal_or_none(row.get("market_share")),
                    "position": row.get("position"),
                    "websites_found": row.get("websites_found") or 0,
                },
            )

    def _upsert_promotion_urls(self, casino, promotions):
        for source_code, value in promotions.items():
            normalized_code = normalize_geo_code(source_code)
            normalized_source_code = str(source_code).lower()
            urls = list(self._promotion_urls(value))
            if not urls:
                continue
            is_default = normalized_code == "default"
            geo = None if is_default else Geo.objects.filter(code=normalized_code).first()
            if not is_default and not geo:
                self.stderr.write("Skipping unknown promotion GEO code %s for %s" % (source_code, casino))
                continue
            for url in urls:
                CasinoBonusPage.objects.update_or_create(
                    casino=casino,
                    geo=geo,
                    source_code=normalized_source_code,
                    url=url,
                    defaults={
                        "is_default": is_default,
                        "is_active": True,
                    },
                )
            CasinoBonusPage.objects.filter(
                casino=casino,
                geo=geo,
                source_code=normalized_source_code,
            ).exclude(url__in=urls).update(is_active=False)

    def _promotion_urls(self, value):
        raw_values = value if isinstance(value, list) else [value]
        for raw_value in raw_values:
            if not raw_value:
                continue
            for url in str(raw_value).split(","):
                url = url.strip()
                if url:
                    yield url

    def _decimal_or_none(self, value):
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return None
