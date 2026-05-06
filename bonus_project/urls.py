"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path

from bonus_telegram_bot import views as telegram_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("bonus_core.urls")),
    path("api/", include("bonus_scraping.urls")),
    path("api/", include("ai_parsing.urls")),
    path("api/telegram/", include("bonus_telegram_bot.urls")),
    path("api/users/", telegram_views.TelegramUserListView.as_view(), name="telegram-user-list-alias"),
    path("api/bonuses/<int:bonus_id>/send/", telegram_views.SendBonusNotificationView.as_view(), name="telegram-send-bonus-alias"),
    path("api/subscriptions/", telegram_views.SubscriptionView.as_view(), name="telegram-subscriptions-alias"),
    path("api/settings/<int:user_id>/", telegram_views.UserSettingsView.as_view(), name="telegram-settings-alias"),
]
