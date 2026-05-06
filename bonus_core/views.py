from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import generics

from bonus_core.models import Bonus, Casino, Geo
from bonus_core.serializers import BonusSerializer, CasinoSerializer, GeoSerializer


class GeoListView(generics.ListAPIView):
    serializer_class = GeoSerializer

    def get_queryset(self):
        queryset = Geo.objects.filter(is_active=True).order_by("sort", "name")
        parent = self.request.query_params.get("parent")
        if parent == "root":
            queryset = queryset.filter(parent__isnull=True)
        elif parent:
            queryset = queryset.filter(parent__code=parent)
        return queryset


class CasinoListView(generics.ListAPIView):
    serializer_class = CasinoSerializer

    def get_queryset(self):
        queryset = Casino.objects.all().order_by("-priority", "name")
        search = self.request.query_params.get("search")
        geo = self.request.query_params.get("geo")
        if search:
            queryset = queryset.filter(name__icontains=search)
        if geo:
            queryset = queryset.filter(locations__geo__code=geo).distinct()
        return queryset


class BonusListView(generics.ListAPIView):
    serializer_class = BonusSerializer

    def get_queryset(self):
        queryset = Bonus.objects.select_related("casino", "geo", "provider", "game")
        casino = self.request.query_params.get("casino")
        geo = self.request.query_params.get("geo")
        bonus_type = self.request.query_params.get("type")
        provider = self.request.query_params.get("provider")
        date_from = parse_date(self.request.query_params.get("date_from") or "")
        date_to = parse_date(self.request.query_params.get("date_to") or "")
        approved = self.request.query_params.get("approved")

        if approved is None:
            queryset = queryset.filter(is_approved=True, is_active=True)
        elif approved in ("1", "true", "True"):
            queryset = queryset.filter(is_approved=True)

        if casino:
            queryset = queryset.filter(Q(casino_id=casino) | Q(casino__name__icontains=casino))
        if geo:
            queryset = queryset.filter(geo__code=geo)
        if bonus_type:
            queryset = queryset.filter(type__iexact=bonus_type)
        if provider:
            queryset = queryset.filter(provider__name__icontains=provider)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-priority", "-casino__priority", "-created_at")


class BonusDetailView(generics.RetrieveAPIView):
    serializer_class = BonusSerializer
    queryset = Bonus.objects.select_related("casino", "geo", "provider", "game")
