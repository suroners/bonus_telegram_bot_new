import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from bonus_core.models import Casino, Geo, ScrapedHistory, ScrapeStatus


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password",
    )


@pytest.fixture
def scraped_history(db):
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino = Casino.objects.create(name="Preview Casino")
    return ScrapedHistory.objects.create(
        casino=casino,
        geo=geo,
        url="https://casino.example/promotions",
        final_url="https://casino.example/promotions/final",
        status=ScrapeStatus.SUCCESS,
        raw_html='<html><head><title>Stored</title></head><body><h1>Stored page</h1><img src="/logo.png"></body></html>',
        scraped_at=timezone.now(),
    )


@pytest.mark.django_db
def test_scraped_history_admin_change_page_shows_mobile_and_web_previews(
    client,
    settings,
    admin_user,
    scraped_history,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    change_url = reverse("admin:bonus_core_scrapedhistory_change", args=[scraped_history.id])
    preview_url = reverse("admin:bonus_core_scrapedhistory_preview", args=[scraped_history.id])

    response = client.get(change_url)

    assert response.status_code == 200
    html = response.content.decode()
    assert "Rendered page preview" in html
    assert "Mobile" in html
    assert "Web" in html
    assert 'id="scraped-preview-mobile-{}"'.format(scraped_history.id) in html
    assert 'id="scraped-preview-web-{}"'.format(scraped_history.id) in html
    assert 'id="scraped-preview-mobile-{}" name="scraped-preview-tab-{}" type="radio" checked'.format(
        scraped_history.id,
        scraped_history.id,
    ) in html
    assert 'class="scraped-preview-frame scraped-preview-mobile-frame"' in html
    assert 'class="scraped-preview-frame scraped-preview-web-frame"' in html
    assert 'src="{}"'.format(preview_url) in html
    assert "Open final URL" in html
    assert "Open raw preview" in html


@pytest.mark.django_db
def test_scraped_history_admin_preview_returns_stored_html_with_final_url_base(
    client,
    settings,
    admin_user,
    scraped_history,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    preview_url = reverse("admin:bonus_core_scrapedhistory_preview", args=[scraped_history.id])

    response = client.get(preview_url)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/html")
    assert "sandbox allow-scripts allow-forms" in response["Content-Security-Policy"]
    assert response["X-Frame-Options"] == "SAMEORIGIN"
    html = response.content.decode()
    assert '<base href="https://casino.example/promotions/final">' in html
    assert "<h1>Stored page</h1>" in html


@pytest.mark.django_db
def test_scraped_history_admin_preview_falls_back_to_source_url_for_base(
    client,
    settings,
    admin_user,
    scraped_history,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    scraped_history.final_url = ""
    scraped_history.save(update_fields=["final_url"])
    client.force_login(admin_user)
    preview_url = reverse("admin:bonus_core_scrapedhistory_preview", args=[scraped_history.id])

    response = client.get(preview_url)

    assert response.status_code == 200
    assert '<base href="https://casino.example/promotions">' in response.content.decode()


@pytest.mark.django_db
def test_scraped_history_admin_preview_requires_admin_login(client, settings, scraped_history):
    settings.ALLOWED_HOSTS = ["testserver"]
    preview_url = reverse("admin:bonus_core_scrapedhistory_preview", args=[scraped_history.id])

    response = client.get(preview_url)

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
