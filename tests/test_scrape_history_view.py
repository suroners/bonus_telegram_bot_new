import pytest
from django.utils import timezone

from bonus_core.models import Casino, CasinoBonusPage, Geo, ScrapedHistory, ScrapeStatus


@pytest.fixture
def scraped_history():
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino = Casino.objects.create(
        name="Same Page Casino",
        logo_url="https://example.com/logo.png",
    )
    bonus_page = CasinoBonusPage.objects.create(
        casino=casino,
        geo=geo,
        url="https://casino.example/promotions",
    )
    return ScrapedHistory.objects.create(
        casino=casino,
        bonus_page=bonus_page,
        geo=geo,
        url="https://casino.example/promotions",
        final_url="https://casino.example/promotions/final",
        status=ScrapeStatus.SUCCESS,
        raw_html="<html>secret raw html</html>",
        aggregator_type="SoftSwiss",
        scraped_at=timezone.now(),
    )


@pytest.mark.django_db
def test_scrape_history_endpoint_renders_responsive_html(client, settings, scraped_history):
    settings.ALLOWED_HOSTS = ["testserver"]

    response = client.get("/api/scrape/history/", HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    html = response.content.decode()
    assert "Scraped History" in html
    assert "desktop-history" in html
    assert "mobile-history" in html
    assert "Same Page Casino" in html
    assert "Admin #{}".format(scraped_history.id) in html
    assert "/admin/bonus_core/scrapedhistory/{}/change/".format(scraped_history.id) in html
    assert "secret raw html" not in html


@pytest.mark.django_db
def test_scrape_history_endpoint_still_returns_json(client, settings, scraped_history):
    settings.ALLOWED_HOSTS = ["testserver"]

    response = client.get("/api/scrape/history/")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["casino_name"] == "Same Page Casino"
    assert "raw_html" not in payload["results"][0]
