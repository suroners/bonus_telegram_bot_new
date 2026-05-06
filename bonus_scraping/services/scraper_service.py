import asyncio
import logging
import time
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from bonus_core.models import AIParsingQueue, CasinoBonusPage, ScrapedHistory, ScrapeStatus
from bonus_scraping.services.aggregator_detector import AggregatorDetector
from bonus_scraping.services.proxy_service import ProxyResolver

logger = logging.getLogger(__name__)


class ScraperService:
    def scrape_single_page(self, page_id, force=False):
        page = CasinoBonusPage.objects.select_related("casino", "geo").get(id=page_id)
        target_url = self._target_url(page.url)

        if not force and self._recent_success_exists(page):
            return ScrapedHistory.objects.create(
                casino=page.casino,
                bonus_page=page,
                url=target_url,
                geo=page.geo,
                scraped_at=timezone.now(),
                status=ScrapeStatus.SKIPPED,
                error_message="Skipped: successful scrape exists in the last 24 hours.",
            )

        last_error = None
        for attempt in range(1, 4):
            try:
                proxy = ProxyResolver.proxy_for_geo(page.geo)
                result = asyncio.run(self._fetch_page(page, target_url=target_url, proxy=proxy))
                aggregator_type = AggregatorDetector.detect(result["html"], result["final_url"] or target_url)
                history = ScrapedHistory.objects.create(
                    casino=page.casino,
                    bonus_page=page,
                    url=target_url,
                    geo=page.geo,
                    scraped_at=timezone.now(),
                    status=ScrapeStatus.SUCCESS,
                    raw_html=result["html"],
                    final_url=result["final_url"],
                    aggregator_type=aggregator_type,
                )
                AIParsingQueue.objects.create(
                    scraped_history=history,
                    scraped_history_id_external=history.id,
                    casino=page.casino,
                    url=target_url,
                    raw_html=result["html"],
                    geo=page.geo,
                )
                if aggregator_type and not page.casino.aggregator_type:
                    page.casino.aggregator_type = aggregator_type
                    page.casino.aggregator_source = result["final_url"] or target_url
                    page.casino.save(update_fields=["aggregator_type", "aggregator_source", "updated_at"])
                return history
            except Exception as exc:  # noqa: BLE001 - store scrape failure reason for ops/admin
                last_error = exc
                logger.exception("Scrape attempt %s failed for page %s", attempt, page.id)
                if attempt < 3:
                    time.sleep(2 ** attempt)

        return ScrapedHistory.objects.create(
            casino=page.casino,
            bonus_page=page,
            url=target_url,
            geo=page.geo,
            scraped_at=timezone.now(),
            status=ScrapeStatus.FAILED,
            error_message=str(last_error),
        )

    def scrape_all(self, force=False):
        histories = []
        for page_id in CasinoBonusPage.objects.filter(is_active=True).values_list("id", flat=True):
            histories.append(self.scrape_single_page(page_id, force=force))
        return histories

    def _recent_success_exists(self, page):
        cutoff = timezone.now() - timedelta(hours=24)
        return ScrapedHistory.objects.filter(
            bonus_page=page,
            status=ScrapeStatus.SUCCESS,
            scraped_at__gte=cutoff,
        ).exists()

    async def _fetch_page(self, page, target_url=None, proxy=None):
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright

        target_url = target_url or self._target_url(page.url)
        async with async_playwright() as playwright:
            launch_kwargs = {"headless": settings.SCRAPER_HEADLESS}
            if proxy:
                launch_kwargs["proxy"] = proxy
            browser = await playwright.chromium.launch(**launch_kwargs)
            context = await browser.new_context()
            try:
                browser_page = await context.new_page()
                await browser_page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=settings.SCRAPER_DEFAULT_TIMEOUT_MS,
                )
                try:
                    await browser_page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.info("Continuing scrape before network idle for page %s", page.id)
                html = await browser_page.content()
                final_url = browser_page.url
            finally:
                await context.close()
                await browser.close()
        return {"html": html, "final_url": final_url}

    def _target_url(self, url):
        for value in str(url).split(","):
            value = value.strip()
            if value:
                return value
        raise ValueError("Casino bonus page has no usable URL.")
