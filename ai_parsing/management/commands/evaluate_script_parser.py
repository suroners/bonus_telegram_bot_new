import re

from django.core.management.base import BaseCommand

from ai_parsing.services.script_parser import ScriptBonusParser
from bonus_core.models import Bonus, ParserReferenceRun, ReferenceRunStatus


class Command(BaseCommand):
    help = "Compare Script Parser output against existing GPT/OpenAI reference bonus rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--reference-provider", default="openai")
        parser.add_argument("--reference-label", default="baseline")

    def handle(self, *args, **options):
        reference_provider = options["reference_provider"]
        reference_label = options["reference_label"]
        limit = options["limit"]
        parser = ScriptBonusParser()
        reference_runs = self._reference_runs(reference_provider, reference_label, limit)

        compared = 0
        total_reference = 0
        total_script = 0
        total_matches = 0
        for reference_run in reference_runs:
            history = reference_run.source_scraped_history
            reference_titles = self._reference_titles(history, reference_provider, reference_label)
            script_titles = [bonus.title for bonus in parser.parse(history.raw_html, source_url=history.url, geo=history.geo)]
            matches = self._matched_titles(reference_titles, script_titles)
            compared += 1
            total_reference += len(reference_titles)
            total_script += len(script_titles)
            total_matches += len(matches)
            self.stdout.write(
                "scrape=%s casino=%s reference=%s script=%s matches=%s"
                % (history.id, history.casino.name, len(reference_titles), len(script_titles), len(matches))
            )

        match_rate = round((total_matches / total_reference) * 100, 2) if total_reference else 0
        self.stdout.write(
            self.style.SUCCESS(
                "Compared %s scrapes: reference=%s script=%s matches=%s match_rate=%s%%"
                % (compared, total_reference, total_script, total_matches, match_rate)
            )
        )

    @staticmethod
    def _reference_runs(reference_provider, reference_label, limit):
        return list(
            ParserReferenceRun.objects.filter(
                provider=reference_provider,
                label=reference_label,
                status=ReferenceRunStatus.SUCCESS,
            )
            .select_related("source_scraped_history__casino", "source_scraped_history__geo")
            .order_by("source_scraped_history_id")[:limit]
        )

    @staticmethod
    def _reference_titles(history, reference_provider, reference_label):
        titles = []
        for bonus in history.bonuses.all():
            if (
                bonus.raw_payload.get("parser_provider") == reference_provider
                and bonus.raw_payload.get("parser_is_reference")
                and bonus.raw_payload.get("parser_reference_label") == reference_label
            ):
                titles.append(bonus.title)
        return titles

    @classmethod
    def _matched_titles(cls, reference_titles, script_titles):
        matches = []
        normalized_script_titles = [cls._normalize_title(title) for title in script_titles]
        for title in reference_titles:
            normalized = cls._normalize_title(title)
            if any(cls._similar_title(normalized, script_title) for script_title in normalized_script_titles):
                matches.append(title)
        return matches

    @staticmethod
    def _normalize_title(title):
        return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()

    @staticmethod
    def _similar_title(reference, candidate):
        if not reference or not candidate:
            return False
        if reference in candidate or candidate in reference:
            return True
        reference_tokens = set(reference.split())
        candidate_tokens = set(candidate.split())
        if not reference_tokens:
            return False
        return len(reference_tokens & candidate_tokens) / len(reference_tokens) >= 0.6
