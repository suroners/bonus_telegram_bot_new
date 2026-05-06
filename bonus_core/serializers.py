from rest_framework import serializers

from bonus_core.models import (
    AIParsingQueue,
    Bonus,
    Casino,
    CasinoBonusPage,
    Geo,
    NotificationHistory,
    ScrapedHistory,
    TelegramUser,
    UserCasinoSubscription,
    UserSettings,
)


class GeoSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True)

    class Meta:
        model = Geo
        fields = [
            "id",
            "source_id",
            "parent",
            "parent_code",
            "code",
            "name",
            "is_regulated",
            "sort",
            "has_ppc",
            "meta",
            "is_active",
        ]


class CasinoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Casino
        fields = [
            "id",
            "source_id",
            "name",
            "slug",
            "type",
            "logo_url",
            "aggregator_type",
            "aggregator_source",
            "priority",
            "my_brand",
        ]


class CasinoBonusPageSerializer(serializers.ModelSerializer):
    casino_name = serializers.CharField(source="casino.name", read_only=True)
    geo_code = serializers.CharField(source="geo.code", read_only=True)

    class Meta:
        model = CasinoBonusPage
        fields = [
            "id",
            "casino",
            "casino_name",
            "geo",
            "geo_code",
            "source_code",
            "url",
            "affiliate_url",
            "is_default",
            "is_active",
            "priority",
            "notes",
            "created_at",
            "updated_at",
        ]


class ScrapedHistorySerializer(serializers.ModelSerializer):
    casino_name = serializers.CharField(source="casino.name", read_only=True)
    geo_code = serializers.CharField(source="geo.code", read_only=True)

    class Meta:
        model = ScrapedHistory
        exclude = ["raw_html"]


class AIParsingQueueSerializer(serializers.ModelSerializer):
    casino_name = serializers.CharField(source="casino.name", read_only=True)
    geo_code = serializers.CharField(source="geo.code", read_only=True)

    class Meta:
        model = AIParsingQueue
        exclude = ["raw_html"]


class BonusSerializer(serializers.ModelSerializer):
    casino_name = serializers.CharField(source="casino.name", read_only=True)
    geo_code = serializers.CharField(source="geo.code", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    game_name = serializers.CharField(source="game.name", read_only=True)

    class Meta:
        model = Bonus
        fields = [
            "id",
            "casino",
            "casino_name",
            "game",
            "game_name",
            "provider",
            "provider_name",
            "title",
            "description",
            "type",
            "wagering_requirement",
            "min_deposit",
            "max_bonus",
            "currency",
            "start_date",
            "end_date",
            "geo",
            "geo_code",
            "bonus_url",
            "is_auto",
            "is_active",
            "is_approved",
            "priority",
            "raw_payload",
            "created_at",
            "updated_at",
        ]


class TelegramUserSerializer(serializers.ModelSerializer):
    geo_code = serializers.CharField(source="geo.code", read_only=True)

    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "telegram_id",
            "username",
            "first_name",
            "last_name",
            "geo",
            "geo_code",
            "created_at",
            "updated_at",
        ]


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = "__all__"


class UserCasinoSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCasinoSubscription
        fields = "__all__"


class NotificationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationHistory
        fields = "__all__"
