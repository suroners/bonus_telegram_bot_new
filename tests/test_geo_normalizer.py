from bonus_core.services.geo_normalizer import normalize_geo_code, parse_geo_meta


def test_normalize_geo_code_maps_known_source_mismatches():
    assert normalize_geo_code("ei") == "ie"
    assert normalize_geo_code("ar-old") == "ar"
    assert normalize_geo_code("CA") == "ca"


def test_parse_geo_meta_accepts_json_string():
    assert parse_geo_meta('{"city": "Dallas"}') == {"city": "Dallas"}
    assert parse_geo_meta("not-json") == {"raw": "not-json"}
