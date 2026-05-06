from django.urls import path

from ai_parsing import views


urlpatterns = [
    path("parse/trigger/<int:scrape_id>/", views.ParseTriggerView.as_view(), name="parse-trigger"),
    path("queue/", views.QueueListView.as_view(), name="ai-queue"),
]
