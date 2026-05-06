from celery import shared_task

from ai_parsing.services.parser_service import ParserService


@shared_task(name="ai_parsing.tasks.parse_single_scrape", queue="ai")
def parse_single_scrape(scrape_message, provider=None):
    bonuses = ParserService().parse_single_scrape(scrape_message, provider=provider)
    return {"bonus_ids": [bonus.id for bonus in bonuses]}


@shared_task(name="ai_parsing.tasks.parse_pending_queue", queue="ai")
def parse_pending_queue(limit=None, provider=None):
    results = ParserService().parse_pending_queue(limit=limit, provider=provider)
    return {"bonus_ids": [bonus.id for group in results for bonus in group]}


@shared_task(name="ai_parsing.tasks.process_llm", queue="ai")
def process_llm(html, casino_id, geo_code=None):
    from bonus_core.models import Geo

    geo = Geo.objects.filter(code=geo_code).first() if geo_code else None
    bonuses = ParserService().process_llm(html, casino_id, geo)
    return [bonus.model_dump(mode="json") for bonus in bonuses]
