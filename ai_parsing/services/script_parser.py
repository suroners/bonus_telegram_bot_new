import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ai_parsing.dtos import ParsedBonusDTO


class ScriptBonusParser:
    model_name = "local-rules-v1"
    keywords = (
        "bonus",
        "promotion",
        "offer",
        "free spin",
        "free bet",
        "cashback",
        "cash back",
        "deposit",
        "welcome",
        "reload",
        "no deposit",
        "rebate",
    )
    stop_phrases = (
        "more info",
        "deposit now",
        "join now",
        "join",
        "sign up",
        "register",
        "terms",
        "terms & conditions",
        "log in",
        "login",
        "play now",
        "claim now",
    )

    def parse(self, html, source_url="", geo=None, max_items=20):
        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
            tag.decompose()

        candidates = self._candidate_blocks(soup)
        bonuses = []
        seen = set()
        for element, title_hint in candidates:
            block_text = self._clean_text(element.get_text(" ", strip=True))
            if not self._looks_like_bonus(block_text):
                continue
            title = self._title_from_text(title_hint or block_text)
            if not title or not self._looks_like_bonus(title + " " + block_text):
                continue

            href = self._first_href(element, source_url)
            key = (self._normalize_key(title), href or "")
            if key in seen:
                continue
            seen.add(key)

            matched_keywords = self._matched_keywords(block_text)
            confidence = self._confidence(block_text, title, matched_keywords, href)
            bonuses.append(
                ParsedBonusDTO(
                    title=title,
                    description=self._description_from_text(block_text, title),
                    type=self._bonus_type(block_text),
                    wagering_requirement=self._wagering_requirement(block_text),
                    min_deposit=self._min_deposit(block_text),
                    max_bonus=self._max_bonus(block_text),
                    currency=self._currency(block_text),
                    geo=geo.code if geo else None,
                    affiliate_url=href,
                    confidence=confidence,
                    matched_keywords=matched_keywords,
                )
            )
            if len(bonuses) >= max_items:
                break
        return bonuses

    def _candidate_blocks(self, soup):
        candidates = {}

        selectors = [
            "[class*='promo' i]",
            "[class*='bonus' i]",
            "[class*='offer' i]",
            "[class*='card' i]",
            "[id*='promo' i]",
            "[id*='bonus' i]",
            "[id*='offer' i]",
        ]
        for selector in selectors:
            for element in soup.select(selector):
                self._append_candidate(candidates, element, "")

        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            heading_text = self._clean_text(heading.get_text(" ", strip=True))
            if not self._looks_like_bonus(heading_text):
                continue
            block = self._nearest_block(heading)
            self._append_candidate(candidates, block, heading_text)

        for link in soup.find_all("a"):
            link_text = self._clean_text(link.get_text(" ", strip=True))
            if self._looks_like_bonus(link_text):
                self._append_candidate(candidates, self._nearest_block(link), link_text)

        return list(candidates.values())

    def _append_candidate(self, candidates, element, title_hint):
        if not element:
            return
        identifier = id(element)
        if identifier in candidates:
            if title_hint and not candidates[identifier][1]:
                candidates[identifier] = (element, title_hint)
            return
        text = self._clean_text(element.get_text(" ", strip=True))
        if len(text) < 12 or len(text) > 2500:
            return
        candidates[identifier] = (element, title_hint)

    def _nearest_block(self, element):
        current = element
        while current.parent and current.name not in ("article", "section", "li"):
            parent_text = self._clean_text(current.parent.get_text(" ", strip=True))
            if 60 <= len(parent_text) <= 1800:
                return current.parent
            current = current.parent
        return current

    def _looks_like_bonus(self, text):
        lowered = text.lower()
        if any(keyword in lowered for keyword in self.keywords):
            return True
        return bool(re.search(r"(\d+\s*%|[€$£]\s*\d+|\d+\s*(?:free\s*)?spins?)", lowered))

    def _title_from_text(self, text):
        cleaned = self._clean_text(text)
        if not cleaned:
            return ""
        lowered = cleaned.lower()
        earliest_stop = len(cleaned)
        for phrase in self.stop_phrases:
            index = lowered.find(phrase)
            if index > 10:
                earliest_stop = min(earliest_stop, index)
        cleaned = cleaned[:earliest_stop].strip(" -|:;,.")

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        title = sentences[0] if sentences else cleaned
        title = re.sub(r"\s+", " ", title).strip(" -|:;,.")
        if len(title) > 140:
            title = self._trim_to_words(title, max_words=16)
        if title.lower() in {"promotions", "promotion", "bonus", "bonuses", "offers"}:
            return ""
        return title[:255]

    def _description_from_text(self, text, title):
        description = self._clean_text(text)
        if title and description.lower().startswith(title.lower()):
            description = description[len(title) :].strip(" -|:;,.")
        return description[:1000]

    def _bonus_type(self, text):
        lowered = text.lower()
        if "no deposit" in lowered:
            return "no_deposit"
        if "cashback" in lowered or "cash back" in lowered or "rebate" in lowered:
            return "cashback"
        if "free spin" in lowered:
            return "free_spins"
        if "free bet" in lowered:
            return "free_bet"
        if "reload" in lowered:
            return "reload_bonus"
        if "welcome" in lowered or "deposit" in lowered:
            return "deposit_bonus"
        return "promotion"

    def _wagering_requirement(self, text):
        patterns = [
            r"(?:wager(?:ing)?(?: requirement)?|playthrough)[^\d]{0,20}(\d+\s*x)",
            r"(\d+\s*x)[^\n.]{0,40}(?:wager|playthrough)",
        ]
        return self._first_match(text, patterns)

    def _min_deposit(self, text):
        patterns = [
            r"(?:min(?:imum)? deposit|deposit)[^\d€$£]{0,25}([€$£]?\s*\d+(?:[.,]\d{1,2})?\+?)",
            r"([€$£]\s*\d+(?:[.,]\d{1,2})?\+?)[^\n.]{0,30}(?:deposit)",
        ]
        return self._first_match(text, patterns)

    def _max_bonus(self, text):
        patterns = [
            r"(?:up to|upto)\s*([€$£]?\s*\d+(?:[.,]\d{1,2})?\s*(?:%|free spins?|spins?)?)",
            r"(\d+\s*%)[^\n.]{0,35}(?:bonus|offer)",
            r"(\d+\s*(?:free\s*)?spins?)",
        ]
        return self._first_match(text, patterns)

    def _currency(self, text):
        if "€" in text:
            return "EUR"
        if "£" in text:
            return "GBP"
        if "$" in text:
            return "USD"
        match = re.search(r"\b(EUR|GBP|USD|CAD|AUD|NZD)\b", text, flags=re.IGNORECASE)
        return match.group(1).upper() if match else None

    def _first_match(self, text, patterns):
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._clean_text(match.group(1))
        return None

    def _first_href(self, element, source_url):
        link = element.find("a", href=True) if hasattr(element, "find") else None
        if not link:
            return None
        href = link.get("href", "").strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            return None
        return urljoin(source_url or "", href)

    def _matched_keywords(self, text):
        lowered = text.lower()
        return [keyword for keyword in self.keywords if keyword in lowered]

    def _confidence(self, text, title, matched_keywords, href):
        score = 0.35
        if title:
            score += 0.2
        score += min(0.25, len(matched_keywords) * 0.06)
        if self._max_bonus(text):
            score += 0.1
        if href:
            score += 0.1
        return round(min(score, 0.95), 2)

    @staticmethod
    def _clean_text(text):
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _normalize_key(text):
        return re.sub(r"[^a-z0-9]+", "", (text or "").lower())

    @staticmethod
    def _trim_to_words(text, max_words):
        words = text.split()
        return " ".join(words[:max_words]).strip()
