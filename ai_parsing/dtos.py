from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ScrapeMessageDTO(BaseModel):
    scrape_id: int
    casino_id: int
    url: str
    scraped_at: Optional[str] = None
    geo: Optional[str] = None


class ParsedBonusDTO(BaseModel):
    title: str
    description: str = ""
    type: str = ""
    game: Optional[str] = None
    provider: Optional[str] = None
    wagering_requirement: Optional[str] = None
    min_deposit: Optional[str] = None
    max_bonus: Optional[str] = None
    currency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    geo: Optional[str] = None
    affiliate_url: Optional[str] = Field(default=None, description="Direct bonus URL from source content.")
    confidence: Optional[float] = None
    matched_keywords: List[str] = Field(default_factory=list)

    @field_validator("description", "type", mode="before")
    @classmethod
    def empty_string_for_nullable_text(cls, value):
        if value is None:
            return ""
        return str(value)

    @field_validator(
        "wagering_requirement",
        "game",
        "min_deposit",
        "max_bonus",
        "currency",
        "provider",
        "geo",
        "affiliate_url",
        mode="before",
    )
    @classmethod
    def stringify_optional(cls, value):
        if value is None:
            return None
        return str(value)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def empty_date_to_none(cls, value):
        if value in (None, "", "n/a", "N/A", "unknown"):
            return None
        return value


class LLMResponseDTO(BaseModel):
    bonuses: List[ParsedBonusDTO]
