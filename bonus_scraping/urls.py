from django.urls import path

from bonus_scraping import views


urlpatterns = [
    path("bonus-pages/", views.BonusPageListView.as_view(), name="bonus-page-list"),
    path("scrape/run/", views.ScrapeRunView.as_view(), name="scrape-run"),
    path("scrape/page/<int:pk>/", views.ScrapePageView.as_view(), name="scrape-page"),
    path("scrape/history/", views.ScrapeHistoryListView.as_view(), name="scrape-history"),
]
