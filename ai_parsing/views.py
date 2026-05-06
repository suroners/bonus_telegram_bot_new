from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_parsing.tasks import parse_single_scrape
from bonus_core.models import AIParsingQueue, ScrapedHistory
from bonus_core.serializers import AIParsingQueueSerializer


class QueueListView(generics.ListAPIView):
    serializer_class = AIParsingQueueSerializer

    def get_queryset(self):
        queryset = AIParsingQueue.objects.select_related("casino", "geo", "scraped_history")
        status_value = self.request.query_params.get("status")
        geo = self.request.query_params.get("geo")
        casino = self.request.query_params.get("casino")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if geo:
            queryset = queryset.filter(geo__code=geo)
        if casino:
            queryset = queryset.filter(casino_id=casino)
        return queryset.order_by("created_at")


class ParseTriggerView(APIView):
    def post(self, request, scrape_id):
        history = ScrapedHistory.objects.get(id=scrape_id)
        AIParsingQueue.objects.get_or_create(
            scraped_history=history,
            defaults={
                "scraped_history_id_external": history.id,
                "casino": history.casino,
                "url": history.url,
                "raw_html": history.raw_html,
                "geo": history.geo,
            },
        )
        task = parse_single_scrape.delay(
            {
                "scrape_id": history.id,
                "casino_id": history.casino_id,
                "url": history.url,
                "scraped_at": history.scraped_at.isoformat(),
                "geo": history.geo.code if history.geo_id else None,
            }
        )
        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
