from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bonus_core.models import TelegramUser, UserCasinoSubscription, UserSettings
from bonus_core.serializers import (
    TelegramUserSerializer,
    UserCasinoSubscriptionSerializer,
    UserSettingsSerializer,
)
from bonus_telegram_bot.tasks import send_bonus_notifications


class TelegramUserListView(generics.ListAPIView):
    serializer_class = TelegramUserSerializer

    def get_queryset(self):
        queryset = TelegramUser.objects.select_related("geo")
        geo = self.request.query_params.get("geo")
        date_from = parse_date(self.request.query_params.get("date_from") or "")
        date_to = parse_date(self.request.query_params.get("date_to") or "")
        if geo:
            queryset = queryset.filter(geo__code=geo)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset.order_by("-created_at")


class SendBonusNotificationView(APIView):
    def post(self, request, bonus_id):
        task = send_bonus_notifications.delay(bonus_id)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class SubscriptionView(APIView):
    def get(self, request):
        queryset = UserCasinoSubscription.objects.select_related("user", "casino")
        serializer = UserCasinoSubscriptionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserCasinoSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        user_id = request.data.get("user")
        casino_id = request.data.get("casino")
        deleted, _ = UserCasinoSubscription.objects.filter(user_id=user_id, casino_id=casino_id).delete()
        return Response({"deleted": deleted})


class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    lookup_field = "user_id"

    def get_queryset(self):
        return UserSettings.objects.select_related("user")
