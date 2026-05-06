from urllib.parse import urljoin

import httpx
from django.conf import settings

from bonus_core.models import Geo, ScraperProxy


class WebshareProxyClient:
    base_url = "https://proxy.webshare.io/api/v2/"

    def __init__(self, token=None, mode=None, timeout=30, http_client=None):
        self.token = token or settings.WEBSHARE_API_TOKEN
        self.mode = mode or settings.WEBSHARE_PROXY_MODE
        self.timeout = timeout
        self.http_client = http_client

    def list_proxies(self, country_codes=None, page_size=100):
        if not self.token:
            raise ValueError("WEBSHARE_API_TOKEN is required to sync Webshare proxies.")

        params = {
            "mode": self.mode,
            "page": 1,
            "page_size": page_size,
        }
        if country_codes:
            params["country_code__in"] = ",".join(country_codes)

        url = urljoin(self.base_url, "proxy/list/")
        while url:
            response = self._get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            yield from payload.get("results", [])
            url = payload.get("next")
            params = None

    def _get(self, url, params=None):
        headers = {"Authorization": "Token %s" % self.token}
        if self.http_client:
            return self.http_client.get(url, headers=headers, params=params)
        return httpx.get(url, headers=headers, params=params, timeout=self.timeout)


class WebshareProxySync:
    provider_prefix = "Webshare "

    def __init__(self, client=None):
        self.client = client or WebshareProxyClient()

    def sync(self, country_codes=None, include_invalid=False, deactivate_missing=True):
        country_codes = country_codes or settings.WEBSHARE_COUNTRY_CODES
        created_count = 0
        updated_count = 0
        skipped_count = 0
        seen_names = set()

        for row in self.client.list_proxies(country_codes=country_codes):
            if not include_invalid and not row.get("valid", False):
                skipped_count += 1
                continue

            name = "%s%s" % (self.provider_prefix, row["id"])
            geo = self._geo_for_country_code(row.get("country_code"))
            proxy, created = ScraperProxy.objects.update_or_create(
                name=name,
                defaults={
                    "geo": geo,
                    "server": self._server_from_row(row),
                    "username": row.get("username") or "",
                    "password": row.get("password") or "",
                    "is_active": True,
                    "priority": 10,
                    "notes": self._notes_from_row(row),
                },
            )
            seen_names.add(proxy.name)
            if created:
                created_count += 1
            else:
                updated_count += 1

        deactivated_count = 0
        if deactivate_missing:
            deactivated_count = ScraperProxy.objects.filter(
                name__startswith=self.provider_prefix,
            ).exclude(name__in=seen_names).update(is_active=False)

        return {
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "deactivated": deactivated_count,
        }

    @staticmethod
    def _server_from_row(row):
        return "http://%s:%s" % (row["proxy_address"], row["port"])

    @staticmethod
    def _geo_for_country_code(country_code):
        if not country_code:
            return None
        geo_code = {"gb": "uk"}.get(country_code.lower(), country_code.lower())
        return Geo.objects.filter(code=geo_code).first()

    @classmethod
    def _notes_from_row(cls, row):
        return "Webshare proxy id: %s; country: %s; city: %s" % (
            row.get("id") or "",
            row.get("country_code") or "",
            row.get("city_name") or "",
        )
