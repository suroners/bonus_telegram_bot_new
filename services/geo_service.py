from asgiref.sync import sync_to_async
from django.db.models import Case, IntegerField, Q, Value, When

from bonus_core.models import Geo


class GeoService:
    PAGE_SIZE = 12
    SEARCH_LIMIT = 8

    @staticmethod
    async def page(page_number=0):
        return await sync_to_async(GeoService._page)(page_number)

    @staticmethod
    def _page(page_number=0):
        page_number = max(int(page_number or 0), 0)
        queryset = Geo.objects.filter(is_active=True).order_by("sort", "name")
        total = queryset.count()
        start = page_number * GeoService.PAGE_SIZE
        end = start + GeoService.PAGE_SIZE
        geos = list(queryset[start:end].values("code", "name", "parent__code"))
        return {
            "page": page_number,
            "total": total,
            "has_prev": page_number > 0,
            "has_next": end < total,
            "geos": geos,
        }

    @staticmethod
    async def search(query, limit=SEARCH_LIMIT):
        return await sync_to_async(GeoService._search)(query, limit)

    @staticmethod
    def _search(query, limit=SEARCH_LIMIT):
        normalized = (query or "").strip()
        if len(normalized) < 2:
            return []

        queryset = (
            Geo.objects.filter(is_active=True)
            .annotate(
                search_rank=Case(
                    When(code__iexact=normalized, then=Value(0)),
                    When(name__iexact=normalized, then=Value(1)),
                    When(code__istartswith=normalized, then=Value(2)),
                    When(name__istartswith=normalized, then=Value(3)),
                    When(code__icontains=normalized, then=Value(4)),
                    When(name__icontains=normalized, then=Value(5)),
                    default=Value(99),
                    output_field=IntegerField(),
                )
            )
            .filter(Q(search_rank__lt=99))
            .order_by("search_rank", "sort", "name")
        )
        limit = max(int(limit or GeoService.SEARCH_LIMIT), 1)
        return list(queryset.values("code", "name", "parent__code")[:limit])
