import pytest

from bonus_core.models import Geo
from bonus_telegram_bot.services.geo_service import GeoService


@pytest.mark.django_db
def test_geo_search_ranks_exact_then_prefix_then_contains_and_skips_inactive():
    Geo.objects.create(code="ab", name="Zulu")
    Geo.objects.create(code="zz", name="ab")
    Geo.objects.create(code="ab-1", name="Later")
    Geo.objects.create(code="cc", name="abacus")
    Geo.objects.create(code="xabx", name="Nothing")
    Geo.objects.create(code="dd", name="zabz")
    Geo.objects.create(code="ab-hidden", name="Hidden", is_active=False)

    results = GeoService._search("ab", limit=10)

    assert [item["code"] for item in results] == ["ab", "zz", "ab-1", "cc", "xabx", "dd"]


@pytest.mark.django_db
def test_geo_search_enforces_limit():
    for index in range(5):
        Geo.objects.create(code="zz-%s" % index, name="Zone ZZ %s" % index)

    results = GeoService._search("zz", limit=3)

    assert len(results) == 3
