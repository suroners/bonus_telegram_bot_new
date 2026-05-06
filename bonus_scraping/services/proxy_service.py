import json
import os
import random
import zlib
from hashlib import sha1
from urllib.parse import unquote, urlsplit, urlunsplit

import httpx
from django.conf import settings

from bonus_core.models import ScraperProxy


class ProxyResolver:
    @classmethod
    def proxy_for_geo(cls, geo):
        db_proxy = cls._proxy_from_database(geo)
        if db_proxy:
            return cls._proxy_from_model(db_proxy)

        raw_proxy = cls._raw_proxy_from_environment(geo)
        if raw_proxy:
            return cls.parse_proxy(raw_proxy)
        return None

    @classmethod
    def parse_proxy(cls, value):
        if isinstance(value, dict):
            proxy = cls.parse_proxy(value.get("server") or value.get("url") or "")
            if value.get("username"):
                proxy["username"] = value["username"]
            if value.get("password"):
                proxy["password"] = value["password"]
            return proxy

        raw_value = str(value or "").strip()
        if not raw_value:
            raise ValueError("Proxy value is empty.")

        shorthand_parts = raw_value.split(":")
        if "://" not in raw_value and len(shorthand_parts) >= 4 and shorthand_parts[1].isdigit():
            host = shorthand_parts[0]
            port = shorthand_parts[1]
            username = shorthand_parts[2]
            password = ":".join(shorthand_parts[3:])
            return {
                "server": "http://%s:%s" % (host, port),
                "username": username,
                "password": password,
            }

        if "://" not in raw_value:
            raw_value = "http://%s" % raw_value

        parsed = urlsplit(raw_value)
        if not parsed.scheme or not parsed.hostname:
            raise ValueError("Invalid proxy value: %s" % value)

        host = parsed.hostname
        if ":" in host and not host.startswith("["):
            host = "[%s]" % host
        if parsed.port:
            host = "%s:%s" % (host, parsed.port)

        proxy = {"server": urlunsplit((parsed.scheme, host, "", "", ""))}
        if parsed.username:
            proxy["username"] = unquote(parsed.username)
        if parsed.password:
            proxy["password"] = unquote(parsed.password)
        return proxy

    @classmethod
    def _proxy_from_database(cls, geo):
        for geo_obj in cls._geo_chain(geo):
            proxy = cls._choose_database_proxy(ScraperProxy.objects.filter(is_active=True, geo=geo_obj))
            if proxy:
                return proxy
        return cls._choose_database_proxy(ScraperProxy.objects.filter(is_active=True, geo__isnull=True))

    @classmethod
    def _proxy_from_model(cls, proxy):
        value = cls.parse_proxy(proxy.server)
        if proxy.username:
            value["username"] = proxy.username
        if proxy.password:
            value["password"] = proxy.password
        return value

    @staticmethod
    def _choose_database_proxy(queryset):
        proxies = list(queryset.order_by("-priority", "id"))
        if not proxies:
            return None
        highest_priority = proxies[0].priority
        highest_priority_proxies = [proxy for proxy in proxies if proxy.priority == highest_priority]
        return random.choice(highest_priority_proxies)

    @classmethod
    def _raw_proxy_from_environment(cls, geo):
        mapping = cls._geo_proxy_map()
        codes = [geo_obj.code for geo_obj in cls._geo_chain(geo)]

        for code in codes:
            specific = os.environ.get("GEO_PROXY_%s" % code.upper().replace("-", "_"))
            if specific:
                return specific
            mapped = mapping.get(code.lower())
            if mapped:
                return mapped

        default_proxy = getattr(settings, "GEO_PROXY_DEFAULT", "")
        if default_proxy:
            return default_proxy

        proxies = getattr(settings, "PROXY_URLS", [])
        if not proxies:
            return None
        key = (codes[0] if codes else "default").encode("utf-8")
        return proxies[zlib.crc32(key) % len(proxies)]

    @staticmethod
    def _geo_chain(geo):
        current = geo
        while current:
            yield current
            current = current.parent

    @staticmethod
    def _geo_proxy_map():
        raw_map = getattr(settings, "GEO_PROXY_MAP", "")
        if not raw_map:
            return {}

        try:
            data = json.loads(raw_map)
        except json.JSONDecodeError:
            data = {}
            for item in raw_map.split(";"):
                code, separator, proxy = item.partition("=")
                if separator and proxy.strip():
                    data[code.strip().lower()] = proxy.strip()
            return data

        if not isinstance(data, dict):
            return {}
        return {str(code).lower(): proxy for code, proxy in data.items() if proxy}


class PublicProxyListClient:
    def __init__(self, source_url=None, timeout=30, http_client=None):
        self.source_url = source_url or settings.PUBLIC_PROXY_LIST_URL
        self.timeout = timeout
        self.http_client = http_client

    def list_proxies(self, limit=None):
        response = self._get(self.source_url)
        response.raise_for_status()
        count = 0
        for line in response.text.splitlines():
            raw_proxy = line.strip()
            if not raw_proxy or raw_proxy.startswith("#"):
                continue
            yield raw_proxy
            count += 1
            if limit and count >= limit:
                return

    def _get(self, url):
        if self.http_client:
            return self.http_client.get(url)
        return httpx.get(url, timeout=self.timeout)


class PublicProxyListSync:
    provider_prefix = "PublicProxy "

    def __init__(self, client=None):
        self.client = client or PublicProxyListClient()

    def sync(self, limit=None, deactivate_missing=True):
        created_count = 0
        updated_count = 0
        skipped_count = 0
        seen_names = set()

        for raw_proxy in self.client.list_proxies(limit=limit):
            try:
                proxy_value = ProxyResolver.parse_proxy(raw_proxy)
            except ValueError:
                skipped_count += 1
                continue

            name = self._name_for_proxy(proxy_value)
            proxy, created = ScraperProxy.objects.update_or_create(
                name=name,
                defaults={
                    "geo": None,
                    "server": proxy_value["server"],
                    "username": proxy_value.get("username", ""),
                    "password": proxy_value.get("password", ""),
                    "is_active": True,
                    "priority": -100,
                    "notes": "Imported from public free proxy list. Use only for testing.",
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

    @classmethod
    def _name_for_proxy(cls, proxy_value):
        source = "%s|%s|%s" % (
            proxy_value["server"],
            proxy_value.get("username", ""),
            proxy_value.get("password", ""),
        )
        return "%s%s" % (cls.provider_prefix, sha1(source.encode("utf-8")).hexdigest()[:12])
