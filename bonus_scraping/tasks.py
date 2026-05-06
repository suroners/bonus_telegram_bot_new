from celery import shared_task

from bonus_core.models import CasinoBonusPage
from bonus_scraping.services.scraper_service import ScraperService


@shared_task(name="bonus_scraping.tasks.scrape_all_casinos", queue="scraper")
def scrape_all_casinos(force=False):
    count = 0
    for page_id in CasinoBonusPage.objects.filter(is_active=True).values_list("id", flat=True):
        scrape_single_page.delay(page_id, force=force)
        count += 1
    return {"queued": count}


@shared_task(name="bonus_scraping.tasks.scrape_single_page", queue="scraper")
def scrape_single_page(page_id, force=False):
    history = ScraperService().scrape_single_page(page_id, force=force)
    return {"history_id": history.id, "status": history.status}
