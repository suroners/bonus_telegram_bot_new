import json
import re
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from ai_parsing.dtos import ParsedBonusDTO
from ai_parsing.services.parser_service import ParserService
from ai_parsing.services.script_parser import ScriptBonusParser
from bonus_core.models import (
    AIParsingQueue,
    AIProviderConfig,
    Bonus,
    Casino,
    Geo,
    ParserReferenceRun,
    QueueStatus,
    ReferenceRunStatus,
    ScrapedHistory,
    ScrapeStatus,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "script_parser_reference.json"


def _normalize_title(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _title_matches(expected, actual):
    expected = _normalize_title(expected)
    actual = _normalize_title(actual)
    return expected in actual or actual in expected


def test_script_parser_matches_gpt_reference_fixture():
    parser = ScriptBonusParser()
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for case in cases:
        bonuses = parser.parse(case["html"], source_url=case["url"])
        titles = [bonus.title for bonus in bonuses]
        for expected_title in case["expected_titles"]:
            assert any(_title_matches(expected_title, title) for title in titles), case["name"]


def test_script_parser_handles_page_without_bonus_blocks():
    parser = ScriptBonusParser()
    html = "<html><body><nav>Home Login Help</nav><p>Responsible gambling information.</p></body></html>"

    assert parser.parse(html, source_url="https://example.test") == []


def test_parsed_bonus_dto_normalizes_nullable_text_fields():
    dto = ParsedBonusDTO.model_validate(
        {
            "title": "GPT Bonus",
            "description": None,
            "type": None,
            "game": 7,
            "provider": 9,
            "geo": 1,
        }
    )

    assert dto.description == ""
    assert dto.type == ""
    assert dto.game == "7"
    assert dto.provider == "9"
    assert dto.geo == "1"


@pytest.mark.django_db
def test_parser_service_script_creates_unapproved_bonus_without_ai_config(settings):
    settings.DEFAULT_PARSER_PROVIDER = "script"
    casino = Casino.objects.create(name="Script Casino")
    geo = Geo.objects.create(code="uk", name="United Kingdom")
    history = ScrapedHistory.objects.create(
        casino=casino,
        url="https://casino.example/promos",
        geo=geo,
        scraped_at=timezone.now(),
        status=ScrapeStatus.SUCCESS,
        raw_html=(
            "<section class='promo-card'><h2>Welcome Bonus 100% up to £200</h2>"
            "<p>Minimum deposit £20. 35x wagering applies.</p>"
            "<a href='/welcome'>Claim bonus</a></section>"
        ),
    )
    queue_item = AIParsingQueue.objects.create(
        scraped_history=history,
        scraped_history_id_external=history.id,
        casino=casino,
        url=history.url,
        raw_html=history.raw_html,
        geo=geo,
    )

    results = ParserService().parse_pending_queue(limit=1, provider="script")

    bonus = results[0][0]
    queue_item.refresh_from_db()
    assert queue_item.status == QueueStatus.DONE
    assert bonus.title == "Welcome Bonus 100% up to £200"
    assert bonus.is_auto is True
    assert bonus.is_approved is False
    assert bonus.bonus_url == "https://casino.example/welcome"
    assert bonus.raw_payload["parser_provider"] == "script"
    assert bonus.raw_payload["parser_model"] == "local-rules-v1"
    assert bonus.raw_payload["parser_is_reference"] is False
    assert bonus.raw_payload["confidence"] is not None


@pytest.mark.django_db
def test_parser_service_openai_provider_path_still_uses_llm_config(monkeypatch):
    class FakeOpenAIProvider:
        def __init__(self, config):
            self.config = config

        def generate(self, prompt):
            return '{"bonuses": [{"title": "GPT Bonus", "description": "Parsed by GPT"}]}'

    monkeypatch.setitem(ParserService.PROVIDERS, "openai", FakeOpenAIProvider)
    AIProviderConfig.objects.create(
        provider="openai",
        model="gpt-test",
        api_key="test-key",
        enabled=True,
    )
    casino = Casino.objects.create(name="GPT Casino")

    result = ParserService().process("<html></html>", casino.id, None, provider="openai")

    assert result.provider == "openai"
    assert result.model == "gpt-test"
    assert [bonus.title for bonus in result.bonuses] == ["GPT Bonus"]


@pytest.mark.django_db
def test_evaluate_script_parser_compares_without_creating_bonuses():
    casino = Casino.objects.create(name="Reference Casino")
    history = ScrapedHistory.objects.create(
        casino=casino,
        url="https://casino.example/promos",
        scraped_at=timezone.now(),
        status=ScrapeStatus.SUCCESS,
        raw_html="<section class='promo'><h2>Reference Welcome Bonus</h2><p>100% bonus offer.</p></section>",
    )
    ParserReferenceRun.objects.create(
        source_scraped_history=history,
        provider="openai",
        model="gpt-test",
        label="baseline",
        status=ReferenceRunStatus.SUCCESS,
        bonus_count=1,
    )
    Bonus.objects.create(
        casino=casino,
        source_scraped_history=history,
        title="Reference Welcome Bonus",
        raw_payload={
            "parser_provider": "openai",
            "parser_model": "gpt-test",
            "parser_is_reference": True,
            "parser_reference_label": "baseline",
        },
    )
    before_count = Bonus.objects.count()
    output = StringIO()

    call_command("evaluate_script_parser", limit=1, stdout=output)

    assert Bonus.objects.count() == before_count
    assert "Compared 1 scrapes" in output.getvalue()


@pytest.mark.django_db
def test_build_reference_dataset_creates_flagged_reference_rows(monkeypatch):
    class FakeOpenAIProvider:
        def __init__(self, config):
            self.config = config

        def generate(self, prompt):
            return '{"bonuses": [{"title": "GPT Bonus", "description": "Parsed by GPT"}]}'

    monkeypatch.setitem(ParserService.PROVIDERS, "openai", FakeOpenAIProvider)
    AIProviderConfig.objects.create(
        provider="openai",
        model="gpt-test",
        api_key="test-key",
        enabled=True,
    )
    casino = Casino.objects.create(name="Reference Builder Casino")
    history = ScrapedHistory.objects.create(
        casino=casino,
        url="https://casino.example/promos",
        scraped_at=timezone.now(),
        status=ScrapeStatus.SUCCESS,
        raw_html="<html><body><h1>bonus page</h1></body></html>",
    )
    output = StringIO()

    call_command(
        "build_reference_dataset",
        provider="openai",
        label="baseline",
        limit=1,
        stdout=output,
    )

    bonus = Bonus.objects.get(source_scraped_history=history)
    reference_run = ParserReferenceRun.objects.get(source_scraped_history=history, provider="openai", label="baseline")
    assert bonus.title == "GPT Bonus"
    assert bonus.raw_payload["parser_provider"] == "openai"
    assert bonus.raw_payload["parser_is_reference"] is True
    assert bonus.raw_payload["parser_reference_label"] == "baseline"
    assert bonus.raw_payload["parser_reference_run_id"] == reference_run.id
    assert reference_run.status == ReferenceRunStatus.SUCCESS
    assert reference_run.model == "gpt-test"
    assert reference_run.bonus_count == 1
    assert "processed=1" in output.getvalue()


@pytest.mark.django_db
def test_evaluate_script_parser_counts_zero_bonus_reference_runs():
    casino = Casino.objects.create(name="Zero Reference Casino")
    history = ScrapedHistory.objects.create(
        casino=casino,
        url="https://casino.example/no-bonus",
        scraped_at=timezone.now(),
        status=ScrapeStatus.SUCCESS,
        raw_html="<html><body><p>Responsible gambling information only.</p></body></html>",
    )
    ParserReferenceRun.objects.create(
        source_scraped_history=history,
        provider="openai",
        model="gpt-test",
        label="baseline",
        status=ReferenceRunStatus.SUCCESS,
        bonus_count=0,
    )
    output = StringIO()

    call_command("evaluate_script_parser", limit=1, stdout=output)

    assert "Compared 1 scrapes: reference=0 script=0 matches=0 match_rate=0%" in output.getvalue()
