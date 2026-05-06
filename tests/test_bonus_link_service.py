import pytest

from bonus_core.models import Bonus, Casino, CasinoBonusPage, Geo
from bonus_core.services.bonus_link_service import BonusLinkService


@pytest.mark.django_db
def test_bonus_link_prefers_manual_affiliate_url():
    geo = Geo.objects.create(code="ca", name="Canada")
    casino = Casino.objects.create(name="Test Casino")
    page = CasinoBonusPage.objects.create(
        casino=casino,
        geo=geo,
        source_code="ca",
        url="https://casino.example/promos",
        affiliate_url="https://affiliate.example/track",
    )
    bonus = Bonus.objects.create(
        casino=casino,
        geo=geo,
        title="100 Free Spins",
        bonus_url="https://casino.example/bonus",
    )

    assert page.affiliate_url
    assert BonusLinkService.resolve_bonus_url(bonus) == "https://affiliate.example/track"


@pytest.mark.django_db
def test_bonus_link_falls_back_to_direct_bonus_url():
    geo = Geo.objects.create(code="uk", name="UK")
    casino = Casino.objects.create(name="Fallback Casino")
    CasinoBonusPage.objects.create(
        casino=casino,
        geo=geo,
        source_code="uk",
        url="https://casino.example/promos",
    )
    bonus = Bonus.objects.create(
        casino=casino,
        geo=geo,
        title="Deposit Bonus",
        bonus_url="https://casino.example/direct-bonus",
    )

    assert BonusLinkService.resolve_bonus_url(bonus) == "https://casino.example/direct-bonus"
