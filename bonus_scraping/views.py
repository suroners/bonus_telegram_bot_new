from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from bonus_core.models import CasinoBonusPage, ScrapedHistory, ScrapeStatus
from bonus_core.serializers import CasinoBonusPageSerializer, ScrapedHistorySerializer
from bonus_scraping.tasks import scrape_all_casinos, scrape_single_page


def _parse_bool(value):
    return str(value).lower() in ("1", "true", "yes", "on")


def _filtered_scrape_history_queryset(params, include_raw_html=False):
    queryset = ScrapedHistory.objects.select_related("casino", "geo", "bonus_page")
    if not include_raw_html:
        queryset = queryset.defer("raw_html")

    casino_id = params.get("casino_id")
    casino = params.get("casino")
    status_value = params.get("status")
    geo = params.get("geo")
    search = params.get("q")
    date_from = parse_date(params.get("date_from") or "")
    date_to = parse_date(params.get("date_to") or "")

    if casino_id:
        if str(casino_id).isdigit():
            queryset = queryset.filter(casino_id=casino_id)
        else:
            queryset = queryset.none()
    if casino:
        queryset = queryset.filter(Q(casino_id=casino) if str(casino).isdigit() else Q(casino__name__icontains=casino))
    if status_value:
        queryset = queryset.filter(status=str(status_value).upper())
    if geo:
        queryset = queryset.filter(geo__code__iexact=geo)
    if search:
        queryset = queryset.filter(
            Q(casino__name__icontains=search)
            | Q(url__icontains=search)
            | Q(final_url__icontains=search)
            | Q(error_message__icontains=search)
            | Q(aggregator_type__icontains=search)
        )
    if date_from:
        queryset = queryset.filter(scraped_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(scraped_at__date__lte=date_to)
    return queryset.order_by("-scraped_at")


class BonusPageListView(generics.ListCreateAPIView):
    serializer_class = CasinoBonusPageSerializer

    def get_queryset(self):
        queryset = CasinoBonusPage.objects.select_related("casino", "geo")
        geo = self.request.query_params.get("geo")
        casino = self.request.query_params.get("casino")
        if geo:
            queryset = queryset.filter(geo__code=geo)
        if casino:
            queryset = queryset.filter(casino_id=casino)
        return queryset.order_by("-priority", "casino__name", "geo__sort")


class ScrapeRunView(APIView):
    def post(self, request):
        force = _parse_bool(request.data.get("force", False))
        task = scrape_all_casinos.delay(force=force)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class ScrapePageView(APIView):
    def post(self, request, pk):
        force = _parse_bool(request.data.get("force", False))
        task = scrape_single_page.delay(pk, force=force)
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class ScrapeHistoryListView(generics.ListAPIView):
    serializer_class = ScrapedHistorySerializer
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = "bonus_scraping/scrape_history_list.html"
    html_paginate_by = 25

    def get_queryset(self):
        return _filtered_scrape_history_queryset(self.request.query_params)

    def get(self, request, *args, **kwargs):
        if request.accepted_renderer.format == "html":
            return self._html_response(request)
        return super().get(request, *args, **kwargs)

    def _html_response(self, request):
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.html_paginate_by)
        page_obj = paginator.get_page(request.GET.get("page"))
        status_params = self.request.GET.copy()
        if "status" in status_params:
            del status_params["status"]
        if "format" in status_params:
            del status_params["format"]
        status_queryset = _filtered_scrape_history_queryset(status_params)
        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]
        if "format" in query_params:
            del query_params["format"]

        return Response(
            {
                "histories": page_obj.object_list,
                "page_obj": page_obj,
                "paginator": paginator,
                "filters": {
                    "q": request.GET.get("q", ""),
                    "casino": request.GET.get("casino", ""),
                    "geo": request.GET.get("geo", ""),
                    "status": request.GET.get("status", ""),
                    "date_from": request.GET.get("date_from", ""),
                    "date_to": request.GET.get("date_to", ""),
                },
                "querystring": query_params.urlencode(),
                "status_choices": ScrapeStatus.choices,
                "status_summary": [
                    {
                        "value": value,
                        "label": label,
                        "count": status_queryset.filter(status=value).count(),
                    }
                    for value, label in ScrapeStatus.choices
                ],
                "total_count": paginator.count,
            },
            template_name=self.template_name,
        )
