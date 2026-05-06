"""Celery app for scraper, parser, and Telegram jobs."""
import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bonus_project.settings")

app = Celery("bonus_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "scrape-all-casinos-daily": {
        "task": "bonus_scraping.tasks.scrape_all_casinos",
        "schedule": crontab(hour=2, minute=0),
    },
    "parse-pending-queue": {
        "task": "ai_parsing.tasks.parse_pending_queue",
        "schedule": crontab(minute="*/10"),
    },
    "broadcast-daily-top-bonuses": {
        "task": "bonus_telegram_bot.tasks.broadcast_daily_top_bonuses",
        "schedule": crontab(hour=12, minute=0),
    },
    "cleanup-old-notifications": {
        "task": "bonus_telegram_bot.tasks.cleanup_old_notifications",
        "schedule": crontab(hour=3, minute=30),
    },
}
