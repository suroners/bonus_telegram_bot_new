import pytest

from bonus_telegram_bot.i18n import CATALOGS, TelegramI18nService, TelegramTranslator, normalize_locale


def test_normalize_locale_uses_primary_language_tag():
    assert normalize_locale("en-GB") == "en"
    assert normalize_locale("ru_RU") == "ru"
    assert normalize_locale("es") is None


def test_resolve_locale_prefers_saved_language_then_telegram_language():
    assert TelegramI18nService.resolve_locale("ru", "en-gb") == "ru"
    assert TelegramI18nService.resolve_locale(None, "ru-RU") == "ru"
    assert TelegramI18nService.resolve_locale(None, "es") == "en"


def test_catalogs_cover_english_base_keys():
    english_keys = set(CATALOGS["en"].keys())

    for locale_code, catalog in CATALOGS.items():
        assert english_keys.issubset(set(catalog.keys())), locale_code


def test_translator_falls_back_to_english_for_missing_locale_key(monkeypatch):
    ru_catalog = dict(CATALOGS["ru"])
    ru_catalog.pop("start.welcome")
    monkeypatch.setitem(CATALOGS, "ru", ru_catalog)

    translator = TelegramTranslator(locale="ru")

    assert translator.t("start.welcome") == CATALOGS["en"]["start.welcome"]


def test_missing_english_key_raises_clear_error(monkeypatch):
    english_catalog = dict(CATALOGS["en"])
    english_catalog.pop("start.welcome")
    monkeypatch.setitem(CATALOGS, "en", english_catalog)

    translator = TelegramTranslator(locale="en")

    with pytest.raises(KeyError, match="Missing translation key: start.welcome"):
        translator.t("start.welcome")
