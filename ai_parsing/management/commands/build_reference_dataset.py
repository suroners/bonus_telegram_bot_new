from django.core.management.base import BaseCommand

from ai_parsing.services.parser_service import ParserService
from bonus_core.models import Bonus, ParserReferenceRun, ReferenceRunStatus, ScrapedHistory, ScrapeStatus


class Command(BaseCommand):
    help = "Parse successful scraped HTML into a flagged reference dataset and persist the run state."

    def add_arguments(self, parser):
        parser.add_argument("--provider", default="openai", choices=("openai", "google", "anthropic", "script"))
        parser.add_argument("--label", default="baseline")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--history-id", type=int, action="append", dest="history_ids")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Rebuild existing reference rows for the same provider and label.",
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        label = options["label"]
        replace = options["replace"]
        service = ParserService()
        summary = {"created_bonuses": 0, "processed": 0, "skipped": 0, "failed": 0}

        for history in self._histories(options["history_ids"], options["limit"]):
            reference_run, _ = ParserReferenceRun.objects.get_or_create(
                source_scraped_history=history,
                provider=provider,
                label=label,
                defaults={"status": ReferenceRunStatus.RUNNING},
            )
            if reference_run.status == ReferenceRunStatus.SUCCESS and not replace:
                summary["skipped"] += 1
                self.stdout.write(
                    "skipped scrape=%s casino=%s existing_reference=%s"
                    % (history.id, history.casino.name, reference_run.bonus_count)
                )
                continue

            reference_run.status = ReferenceRunStatus.RUNNING
            reference_run.model = ""
            reference_run.bonus_count = 0
            reference_run.error_message = ""
            reference_run.save(update_fields=["status", "model", "bonus_count", "error_message", "updated_at"])
            self._delete_existing_reference_bonuses(history, provider, label)

            try:
                result = service.process(
                    history.raw_html,
                    history.casino_id,
                    history.geo,
                    provider=provider,
                    source_url=history.url,
                )
                bonuses = service.save_history_result(
                    history,
                    result,
                    is_reference=True,
                    reference_label=label,
                    reference_run_id=reference_run.id,
                )
                reference_run.model = result.model
                reference_run.status = ReferenceRunStatus.SUCCESS
                reference_run.bonus_count = len(bonuses)
                reference_run.save(update_fields=["model", "status", "bonus_count", "updated_at"])
                summary["created_bonuses"] += len(bonuses)
                summary["processed"] += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        "scrape=%s casino=%s bonuses=%s"
                        % (history.id, history.casino.name, len(bonuses))
                    )
                )
            except Exception as exc:  # noqa: BLE001 - keep batch running across histories
                reference_run.status = ReferenceRunStatus.FAILED
                reference_run.error_message = str(exc)
                reference_run.save(update_fields=["status", "error_message", "updated_at"])
                summary["failed"] += 1
                self.stdout.write(
                    self.style.ERROR(
                        "scrape=%s casino=%s failed=%s" % (history.id, history.casino.name, exc)
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Reference dataset provider=%s label=%s processed=%s skipped=%s failed=%s created_bonuses=%s"
                % (
                    provider,
                    label,
                    summary["processed"],
                    summary["skipped"],
                    summary["failed"],
                    summary["created_bonuses"],
                )
            )
        )

    @staticmethod
    def _histories(history_ids, limit):
        queryset = ScrapedHistory.objects.filter(status=ScrapeStatus.SUCCESS).select_related("casino", "geo").order_by("id")
        if history_ids:
            queryset = queryset.filter(id__in=history_ids)
        if limit:
            queryset = queryset[:limit]
        return queryset

    @staticmethod
    def _delete_existing_reference_bonuses(history, provider, label):
        ids_to_delete = []
        for bonus in history.bonuses.all():
            if (
                bonus.raw_payload.get("parser_is_reference")
                and bonus.raw_payload.get("parser_provider") == provider
                and bonus.raw_payload.get("parser_reference_label") == label
            ):
                ids_to_delete.append(bonus.id)
        if ids_to_delete:
            Bonus.objects.filter(id__in=ids_to_delete).delete()
