from django.urls import path

from bonus_telegram_bot import views


urlpatterns = [
    path("users/", views.TelegramUserListView.as_view(), name="telegram-user-list"),
    path("bonuses/<int:bonus_id>/send/", views.SendBonusNotificationView.as_view(), name="telegram-send-bonus"),
    path("subscriptions/", views.SubscriptionView.as_view(), name="telegram-subscriptions"),
    path("settings/<int:user_id>/", views.UserSettingsView.as_view(), name="telegram-settings"),
]
