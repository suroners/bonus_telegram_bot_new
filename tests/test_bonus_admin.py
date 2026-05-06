import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from bonus_core.models import Bonus, Casino, Geo


@pytest.fixture
def admin_user(db):
    return get_user_model().objects.create_superuser(
        username="bonus-admin",
        email="bonus-admin@example.com",
        password="password",
    )


@pytest.fixture
def bonus_records(db):
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    casino = Casino.objects.create(name="Approve Casino")
    unapproved_bonus = Bonus.objects.create(
        casino=casino,
        geo=geo,
        title="Needs Review",
        is_approved=False,
    )
    approved_bonus = Bonus.objects.create(
        casino=casino,
        geo=geo,
        title="Already Approved",
        is_approved=True,
    )
    return {"unapproved": unapproved_bonus, "approved": approved_bonus}


@pytest.mark.django_db
def test_bonus_admin_changelist_shows_approve_and_unapprove_buttons(
    client,
    settings,
    admin_user,
    bonus_records,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    changelist_url = reverse("admin:bonus_core_bonus_changelist")
    toggle_unapproved_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus_records["unapproved"].id])
    toggle_approved_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus_records["approved"].id])

    response = client.get(changelist_url)

    assert response.status_code == 200
    html = response.content.decode()
    assert "Approve" in html
    assert "Unapprove" in html
    assert 'action="{}"'.format(toggle_unapproved_url) in html
    assert 'action="{}"'.format(toggle_approved_url) in html
    assert 'form="bonus-approval-form-{}"'.format(bonus_records["unapproved"].id) in html
    assert 'form="bonus-approval-form-{}"'.format(bonus_records["approved"].id) in html
    assert 'id="bonus-approval-form-{}"'.format(bonus_records["unapproved"].id) in html
    assert 'id="bonus-approval-form-{}"'.format(bonus_records["approved"].id) in html
    assert 'name="next" value="{}"'.format(changelist_url) in html
    assert html.index('id="changelist-form"') < html.index('id="bonus-approval-form-{}"'.format(bonus_records["unapproved"].id))


@pytest.mark.django_db
def test_bonus_admin_toggle_approval_post_approves_bonus(
    client,
    settings,
    admin_user,
    bonus_records,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    bonus = bonus_records["unapproved"]
    toggle_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus.id])
    next_url = reverse("admin:bonus_core_bonus_changelist") + "?is_approved__exact=0"

    response = client.post(toggle_url, {"next": next_url}, follow=False)

    bonus.refresh_from_db()
    assert response.status_code == 302
    assert response["Location"] == next_url
    assert bonus.is_approved is True


@pytest.mark.django_db
def test_bonus_admin_toggle_approval_post_unapproves_bonus(
    client,
    settings,
    admin_user,
    bonus_records,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    bonus = bonus_records["approved"]
    toggle_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus.id])

    response = client.post(toggle_url, {"next": reverse("admin:bonus_core_bonus_changelist")}, follow=False)

    bonus.refresh_from_db()
    assert response.status_code == 302
    assert bonus.is_approved is False


@pytest.mark.django_db
def test_bonus_admin_toggle_approval_get_does_not_mutate(
    client,
    settings,
    admin_user,
    bonus_records,
):
    settings.ALLOWED_HOSTS = ["testserver"]
    client.force_login(admin_user)
    bonus = bonus_records["unapproved"]
    toggle_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus.id])

    response = client.get(toggle_url)

    bonus.refresh_from_db()
    assert response.status_code == 405
    assert bonus.is_approved is False


@pytest.mark.django_db
def test_bonus_admin_toggle_approval_requires_admin_login(client, settings, bonus_records):
    settings.ALLOWED_HOSTS = ["testserver"]
    toggle_url = reverse("admin:bonus_core_bonus_toggle_approval", args=[bonus_records["unapproved"].id])

    response = client.post(toggle_url, {"next": reverse("admin:bonus_core_bonus_changelist")}, follow=False)

    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
