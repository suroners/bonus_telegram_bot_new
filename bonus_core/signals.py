from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from bonus_core.models import Bonus, TelegramUser, UserSettings
from bonus_telegram_bot.tasks import send_bonus_notifications


@receiver(post_save, sender=TelegramUser)
def ensure_user_settings(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.get_or_create(user=instance)


@receiver(pre_save, sender=Bonus)
def capture_bonus_approval_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_is_approved = None
        return
    instance._previous_is_approved = sender.objects.filter(pk=instance.pk).values_list("is_approved", flat=True).first()


@receiver(post_save, sender=Bonus)
def enqueue_bonus_notifications_on_approval(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    became_approved = instance.is_approved and (
        created or getattr(instance, "_previous_is_approved", None) is False
    )
    if not settings.TELEGRAM_BOT_TOKEN or not became_approved or not instance.is_active:
        return
    transaction.on_commit(lambda: send_bonus_notifications.delay(instance.id))
