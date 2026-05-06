import pytest

from bonus_core.models import Bonus, Casino


@pytest.mark.django_db
def test_bonus_approval_transition_enqueues_notification(monkeypatch, django_capture_on_commit_callbacks, settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    casino = Casino.objects.create(name="Signal Casino")
    bonus = Bonus.objects.create(casino=casino, title="Needs Approval", is_active=True, is_approved=False)
    queued_bonus_ids = []

    monkeypatch.setattr("bonus_core.signals.send_bonus_notifications.delay", lambda bonus_id: queued_bonus_ids.append(bonus_id))

    with django_capture_on_commit_callbacks(execute=True):
        bonus.is_approved = True
        bonus.save(update_fields=["is_approved", "updated_at"])

    assert queued_bonus_ids == [bonus.id]


@pytest.mark.django_db
def test_bonus_save_without_new_approval_does_not_enqueue_notification(monkeypatch, django_capture_on_commit_callbacks, settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    casino = Casino.objects.create(name="No Queue Casino")
    queued_bonus_ids = []

    monkeypatch.setattr("bonus_core.signals.send_bonus_notifications.delay", lambda bonus_id: queued_bonus_ids.append(bonus_id))
    with django_capture_on_commit_callbacks(execute=True):
        bonus = Bonus.objects.create(casino=casino, title="Already Approved", is_active=True, is_approved=True)
    queued_bonus_ids.clear()

    with django_capture_on_commit_callbacks(execute=True):
        bonus.title = "Edited Title"
        bonus.save(update_fields=["title", "updated_at"])

    assert queued_bonus_ids == []


@pytest.mark.django_db
def test_inactive_approved_bonus_does_not_enqueue_notification(monkeypatch, django_capture_on_commit_callbacks, settings):
    settings.TELEGRAM_BOT_TOKEN = "test-token"
    casino = Casino.objects.create(name="Inactive Casino")
    queued_bonus_ids = []

    monkeypatch.setattr("bonus_core.signals.send_bonus_notifications.delay", lambda bonus_id: queued_bonus_ids.append(bonus_id))

    with django_capture_on_commit_callbacks(execute=True):
        Bonus.objects.create(casino=casino, title="Inactive Approved", is_active=False, is_approved=True)

    assert queued_bonus_ids == []
