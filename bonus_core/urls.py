from django.urls import path

from bonus_core import views


urlpatterns = [
    path("geos/", views.GeoListView.as_view(), name="geo-list"),
    path("casinos/", views.CasinoListView.as_view(), name="casino-list"),
    path("bonuses/", views.BonusListView.as_view(), name="bonus-list"),
    path("bonus/<int:pk>/", views.BonusDetailView.as_view(), name="bonus-detail"),
]
