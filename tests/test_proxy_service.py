import pytest

from bonus_core.models import Geo, ScraperProxy
from bonus_scraping.services.proxy_service import PublicProxyListClient, PublicProxyListSync, ProxyResolver


def test_parse_authenticated_proxy_url():
    assert ProxyResolver.parse_proxy("http://user:pass@proxy.example:8000") == {
        "server": "http://proxy.example:8000",
        "username": "user",
        "password": "pass",
    }


def test_parse_host_port_username_password_proxy():
    assert ProxyResolver.parse_proxy("proxy.example:8000:user:pass") == {
        "server": "http://proxy.example:8000",
        "username": "user",
        "password": "pass",
    }


@pytest.mark.django_db
def test_database_geo_proxy_takes_priority_over_environment(settings):
    settings.PROXY_URLS = ["http://fallback.example:9000"]
    settings.GEO_PROXY_DEFAULT = ""
    settings.GEO_PROXY_MAP = ""
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    ScraperProxy.objects.create(
        geo=geo,
        server="http://db.example:9000",
        username="db-user",
        password="db-pass",
    )

    assert ProxyResolver.proxy_for_geo(geo) == {
        "server": "http://db.example:9000",
        "username": "db-user",
        "password": "db-pass",
    }


@pytest.mark.django_db
def test_geo_proxy_map_supports_authenticated_values(settings, monkeypatch):
    monkeypatch.delenv("GEO_PROXY_UK", raising=False)
    settings.PROXY_URLS = []
    settings.GEO_PROXY_DEFAULT = ""
    settings.GEO_PROXY_MAP = '{"uk": "socks5://map-user:map-pass@uk-proxy.example:1080"}'
    geo = Geo.objects.create(code="uk", name="United Kingdom")

    assert ProxyResolver.proxy_for_geo(geo) == {
        "server": "socks5://uk-proxy.example:1080",
        "username": "map-user",
        "password": "map-pass",
    }


@pytest.mark.django_db
def test_child_geo_uses_parent_geo_proxy(settings):
    settings.PROXY_URLS = []
    settings.GEO_PROXY_DEFAULT = ""
    settings.GEO_PROXY_MAP = ""
    country = Geo.objects.create(code="us", name="United States")
    state = Geo.objects.create(code="us-nj", name="New Jersey", parent=country)
    ScraperProxy.objects.create(geo=country, server="http://us-proxy.example:9000")

    assert ProxyResolver.proxy_for_geo(state) == {
        "server": "http://us-proxy.example:9000",
    }


@pytest.mark.django_db
def test_database_proxy_resolver_uses_highest_priority(settings, monkeypatch):
    settings.PROXY_URLS = []
    settings.GEO_PROXY_DEFAULT = ""
    settings.GEO_PROXY_MAP = ""
    monkeypatch.setattr("bonus_scraping.services.proxy_service.random.choice", lambda values: values[0])
    ScraperProxy.objects.create(server="http://low.example:9000", priority=-100)
    ScraperProxy.objects.create(server="http://high.example:9000", priority=10)

    assert ProxyResolver.proxy_for_geo(None) == {"server": "http://high.example:9000"}


class FakeTextResponse:
    text = """
    # comment
    http://1.2.3.4:8000
    5.6.7.8:9000
    """

    def raise_for_status(self):
        return None


class FakeTextHttpClient:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeTextResponse()


@pytest.mark.django_db
def test_public_proxy_list_sync_imports_plain_text_proxies():
    http_client = FakeTextHttpClient()
    client = PublicProxyListClient(source_url="https://example.test/proxies.txt", http_client=http_client)

    result = PublicProxyListSync(client=client).sync(limit=10)

    assert result == {"created": 2, "updated": 0, "skipped": 0, "deactivated": 0}
    assert http_client.urls == ["https://example.test/proxies.txt"]
    assert list(ScraperProxy.objects.order_by("server").values_list("server", "priority", "notes")) == [
        ("http://1.2.3.4:8000", -100, "Imported from public free proxy list. Use only for testing."),
        ("http://5.6.7.8:9000", -100, "Imported from public free proxy list. Use only for testing."),
    ]
