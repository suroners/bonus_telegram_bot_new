from celery import shared_task

from bonus_telegram_bot.services.notification_service import TelegramNotificationService


@shared_task(name="bonus_telegram_bot.tasks.send_bonus_notifications", queue="default")
def send_bonus_notifications(bonus_id):
    return TelegramNotificationService().send_bonus_notifications(bonus_id)


@shared_task(name="bonus_telegram_bot.tasks.broadcast_daily_top_bonuses", queue="default")
def broadcast_daily_top_bonuses():
    return TelegramNotificationService().broadcast_daily_top_bonuses()


@shared_task(name="bonus_telegram_bot.tasks.cleanup_old_notifications", queue="default")
def cleanup_old_notifications(days=90):
    return TelegramNotificationService().cleanup_old_notifications(days=days)
