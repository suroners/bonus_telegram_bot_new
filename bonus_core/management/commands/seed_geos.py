import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from bonus_core.models import Geo
from bonus_core.services.geo_normalizer import normalize_geo_code, parse_geo_meta


class Command(BaseCommand):
    help = "Seed GEO rows from bonus_scraping/geo-big.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR / "bonus_scraping" / "geo-big.json"),
            help="Path to geo-big.json",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise FileNotFoundError("GEO seed file not found: %s" % path)

        with path.open("r", encoding="utf-8") as file_handle:
            rows = json.load(file_handle)

        geos_by_source_id = {}
        for row in rows:
            code = normalize_geo_code(row["code"])
            geo, _ = Geo.objects.update_or_create(
                code=code,
                defaults={
                    "source_id": row.get("id"),
                    "name": row.get("name") or code.upper(),
                    "is_regulated": bool(row.get("is_regulated")),
                    "sort": row.get("sort") or 0,
                    "has_ppc": bool(row.get("has_ppc")),
                    "meta": parse_geo_meta(row.get("meta")),
                    "is_active": True,
                },
            )
            geos_by_source_id[row.get("id")] = geo

        for row in rows:
            geo = geos_by_source_id.get(row.get("id"))
            parent_id = row.get("parent_id")
            parent = geos_by_source_id.get(parent_id) if parent_id else None
            if geo and geo.parent_id != (parent.id if parent else None):
                geo.parent = parent
                geo.save(update_fields=["parent", "updated_at"])

        if not Geo.objects.filter(code="mt").exists():
            Geo.objects.create(
                code="mt",
                name="Malta",
                sort=106,
                is_regulated=False,
                has_ppc=False,
                meta={"seeded_from": "promotion_code"},
            )

        self.stdout.write(self.style.SUCCESS("Seeded %s GEO rows" % Geo.objects.count()))
