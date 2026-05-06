import json
import logging
import re
import traceback
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ai_parsing.dtos import LLMResponseDTO, ParsedBonusDTO, ScrapeMessageDTO
from ai_parsing.services.llm_providers.anthropic_provider import AnthropicProvider
from ai_parsing.services.llm_providers.google_provider import GoogleProvider
from ai_parsing.services.llm_providers.openai_provider import OpenAIProvider
from ai_parsing.services.script_parser import ScriptBonusParser
from bonus_core.models import (
    AIParsingQueue,
    AIProviderConfig,
    Bonus,
    Geo,
    QueueStatus,
    ScrapedHistory,
)
from bonus_core.repository import AIParsingQueueRepository, BonusRepository
from bonus_core.services.geo_normalizer import normalize_geo_code

logger = logging.getLogger(__name__)


@dataclass
class ParserResult:
    bonuses: list
    provider: str
    model: str


class ParserService:
    PROVIDERS = {
        AIProviderConfig.PROVIDER_OPENAI: OpenAIProvider,
        AIProviderConfig.PROVIDER_GOOGLE: GoogleProvider,
        AIProviderConfig.PROVIDER_ANTHROPIC: AnthropicProvider,
    }

    def __init__(self):
        self.queue_repository = AIParsingQueueRepository()
        self.bonus_repository = BonusRepository()

    def parse_single_scrape(self, scrape_message, provider=None):
        dto = ScrapeMessageDTO.model_validate(scrape_message)
        queue_item = AIParsingQueue.objects.filter(scraped_history_id_external=dto.scrape_id).first()
        if not queue_item:
            history = ScrapedHistory.objects.get(id=dto.scrape_id)
            queue_item = AIParsingQueue.objects.create(
                scraped_history=history,
                scraped_history_id_external=history.id,
                casino=history.casino,
                url=history.url,
                raw_html=history.raw_html,
                geo=history.geo,
            )
        return self.parse_queue_item(queue_item.id, provider=provider)

    def parse_pending_queue(self, limit=None, provider=None):
        items = self.queue_repository.get_pending_queue_items()
        if limit:
            items = items[:limit]
        results = []
        for item in items:
            results.append(self.parse_queue_item(item.id, provider=provider))
        return results

    def parse_queue_item(self, queue_item_id, provider=None):
        with transaction.atomic():
            queue_item = AIParsingQueue.objects.select_for_update().select_related("casino").get(id=queue_item_id)
            if queue_item.status == QueueStatus.PROCESSING:
                return []
            queue_item.status = QueueStatus.PROCESSING
            queue_item.error_message = ""
            queue_item.traceback = ""
            queue_item.save(update_fields=["status", "error_message", "traceback", "updated_at"])

        try:
            result = self.process(
                queue_item.raw_html,
                queue_item.casino_id,
                queue_item.geo,
                provider=provider,
                source_url=queue_item.url,
            )
            bonuses = [
                self.create_bonus_from_source(
                    casino=queue_item.casino,
                    source_scraped_history=queue_item.scraped_history,
                    source_url=queue_item.url,
                    geo=queue_item.geo,
                    dto=dto,
                    parser_provider=result.provider,
                    parser_model=result.model,
                )
                for dto in result.bonuses
            ]
            self.queue_repository.update_queue_status(queue_item, QueueStatus.DONE)
            return bonuses
        except Exception as exc:  # noqa: BLE001 - persist parser failure for admin review
            logger.exception("AI parsing failed for queue item %s", queue_item_id)
            self.queue_repository.update_queue_status(
                queue_item,
                QueueStatus.FAILED,
                error_message=str(exc),
                traceback_text=traceback.format_exc(),
            )
            raise

    def process(self, html, casino_id, geo, provider=None, source_url=""):
        provider_key = provider or settings.DEFAULT_PARSER_PROVIDER
        if provider_key == AIProviderConfig.PROVIDER_SCRIPT:
            parser = ScriptBonusParser()
            return ParserResult(
                bonuses=parser.parse(html, source_url=source_url, geo=geo),
                provider=AIProviderConfig.PROVIDER_SCRIPT,
                model=parser.model_name,
            )

        config = self._select_provider_config(provider=provider_key, allow_fallback=provider is None)
        return ParserResult(
            bonuses=self._process_llm_with_config(config, html, casino_id, geo),
            provider=config.provider,
            model=config.model,
        )

    def process_llm(self, html, casino_id, geo):
        config = self._select_provider_config(provider=settings.DEFAULT_LLM_PROVIDER)
        return self._process_llm_with_config(config, html, casino_id, geo)

    def save_history_result(
        self,
        history,
        result,
        *,
        is_reference=False,
        reference_label="baseline",
        reference_run_id=None,
    ):
        return [
            self.create_bonus_from_source(
                casino=history.casino,
                source_scraped_history=history,
                source_url=history.url,
                geo=history.geo,
                dto=dto,
                parser_provider=result.provider,
                parser_model=result.model,
                parser_is_reference=is_reference,
                parser_reference_label=reference_label,
                parser_reference_run_id=reference_run_id,
            )
            for dto in result.bonuses
        ]

    def _process_llm_with_config(self, config, html, casino_id, geo):
        provider_class = self.PROVIDERS.get(config.provider)
        if not provider_class:
            raise ValueError("Unsupported AI provider: %s" % config.provider)
        prompt = self._build_prompt(html, casino_id, geo)
        content = provider_class(config).generate(prompt)
        payload = self._extract_json(content)
        if isinstance(payload, list):
            response = LLMResponseDTO(bonuses=[ParsedBonusDTO.model_validate(item) for item in payload])
        elif "bonuses" in payload:
            response = LLMResponseDTO.model_validate(payload)
        else:
            response = LLMResponseDTO(bonuses=[ParsedBonusDTO.model_validate(payload)])
        return response.bonuses

    def _select_provider_config(self, provider=None, allow_fallback=False):
        if provider:
            config = (
                AIProviderConfig.objects.filter(enabled=True, provider=provider)
                .order_by("priority", "updated_at")
                .first()
            )
            if config:
                return config
            if not allow_fallback:
                raise ValueError("No enabled parser provider is configured for %s." % provider)

        config = AIProviderConfig.objects.filter(enabled=True).order_by("priority", "updated_at").first()
        if config:
            return config
        raise ValueError("No enabled AI provider is configured in AIProviderConfig.")

    def _build_prompt(self, html, casino_id, geo):
        geo_code = geo.code if geo else ""
        trimmed_html = (html or "")[:120000]
        return (
            "Extract all casino bonuses from this scraped HTML.\n"
            "Return strict JSON. The JSON may be either an object with a `bonuses` array or a single bonus object.\n"
            "Each bonus must contain: title, description, type, game, provider, wagering_requirement, "
            "min_deposit, max_bonus, currency, start_date, end_date, geo, affiliate_url.\n"
            "Use affiliate_url for the direct source bonus URL only; manual affiliate redirects are managed elsewhere.\n"
            "casino_id=%s geo=%s scraped_at=%s\n\nHTML:\n%s"
            % (casino_id, geo_code, timezone.now().isoformat(), trimmed_html)
        )

    def _extract_json(self, content):
        text = (content or "").strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            text = fenced.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = min([idx for idx in [text.find("{"), text.find("[")] if idx >= 0], default=-1)
            end = max(text.rfind("}"), text.rfind("]"))
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
            raise

    def create_bonus_from_source(
        self,
        *,
        casino,
        source_scraped_history,
        source_url,
        geo,
        dto,
        parser_provider="",
        parser_model="",
        parser_is_reference=False,
        parser_reference_label="",
        parser_reference_run_id=None,
    ):
        if dto.geo:
            geo = Geo.objects.filter(code=normalize_geo_code(dto.geo)).first() or geo
        provider, game = self.bonus_repository.link_game_provider(dto.provider, dto.game)
        raw_payload = dto.model_dump(mode="json")
        raw_payload["parser_provider"] = parser_provider
        raw_payload["parser_model"] = parser_model
        raw_payload["parser_is_reference"] = parser_is_reference
        raw_payload["parser_reference_label"] = parser_reference_label or ""
        if parser_reference_run_id is not None:
            raw_payload["parser_reference_run_id"] = parser_reference_run_id

        bonus = Bonus.objects.create(
            casino=casino,
            source_scraped_history=source_scraped_history,
            game=game,
            provider=provider,
            title=dto.title,
            description=dto.description or "",
            type=dto.type or "",
            wagering_requirement=dto.wagering_requirement or "",
            min_deposit=dto.min_deposit or "",
            max_bonus=dto.max_bonus or "",
            currency=dto.currency or "",
            start_date=dto.start_date,
            end_date=dto.end_date,
            geo=geo,
            bonus_url=dto.affiliate_url or source_url,
            is_auto=True,
            is_active=True,
            is_approved=False,
            raw_payload=raw_payload,
        )
        return bonus
