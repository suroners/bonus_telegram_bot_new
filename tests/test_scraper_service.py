import pytest

from bonus_core.models import AIParsingQueue, Casino, CasinoBonusPage, Geo, ScrapeStatus, ScraperProxy
from bonus_scraping.services.scraper_service import ScraperService


@pytest.mark.django_db
def test_scrape_single_page_resolves_database_proxy_before_async_fetch(settings, monkeypatch):
    settings.PROXY_URLS = []
    settings.GEO_PROXY_DEFAULT = ""
    settings.GEO_PROXY_MAP = ""
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino = Casino.objects.create(name="Test Casino")
    page = CasinoBonusPage.objects.create(
        casino=casino,
        geo=geo,
        url="https://casino.example/promotions",
    )
    ScraperProxy.objects.create(geo=geo, server="http://db-proxy.example:9000")
    fetch_call = {}

    async def fake_fetch_page(self, page_arg, target_url=None, proxy=None):
        fetch_call["page"] = page_arg
        fetch_call["target_url"] = target_url
        fetch_call["proxy"] = proxy
        return {"html": "<html>bonus</html>", "final_url": target_url}

    monkeypatch.setattr(ScraperService, "_fetch_page", fake_fetch_page)

    history = ScraperService().scrape_single_page(page.id, force=True)

    assert history.status == ScrapeStatus.SUCCESS
    assert fetch_call == {
        "page": page,
        "target_url": "https://casino.example/promotions",
        "proxy": {"server": "http://db-proxy.example:9000"},
    }
    assert AIParsingQueue.objects.filter(scraped_history=history).exists()
