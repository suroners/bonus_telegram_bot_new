import json


GEO_CODE_ALIASES = {
    "ei": "ie",
    "ar-old": "ar",
}


def normalize_geo_code(code):
    if code is None:
        return None
    normalized = str(code).strip().lower()
    return GEO_CODE_ALIASES.get(normalized, normalized)


def parse_geo_meta(raw_meta):
    if raw_meta in (None, ""):
        return None
    if isinstance(raw_meta, dict):
        return raw_meta
    if isinstance(raw_meta, str):
        try:
            return json.loads(raw_meta)
        except json.JSONDecodeError:
            return {"raw": raw_meta}
    return raw_meta
