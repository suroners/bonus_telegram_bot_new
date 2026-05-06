from html import escape

from bonus_telegram_bot.i18n import TelegramI18nService


def format_bonus_cards(cards, translator=None):
    translator = translator or TelegramI18nService.translator()
    if not cards:
        return translator.t("bonuses.empty")
    parts = []
    for card in cards:
        title = escape(card["title"])
        casino = escape(card["casino"])
        geo_value = card["geo"]
        if geo_value == "GLOBAL":
            geo_value = translator.t("bonuses.geo.global")
        geo = escape(geo_value)
        bonus_type = escape(card["type"] or translator.t("bonuses.card.fallback_type"))
        description = escape((card["description"] or "").strip())
        if len(description) > 220:
            description = description[:217] + "..."
        link = ""
        if card["url"]:
            link = '\n<a href="%s">%s</a>' % (
                escape(card["url"], quote=True),
                escape(translator.t("bonuses.card.open_link")),
            )
        parts.append("<b>%s</b>\n%s | %s | %s\n%s%s" % (title, casino, geo, bonus_type, description, link))
    return "\n\n".join(parts)


def settings_text(snapshot, translator):
    return translator.t(
        "settings.screen",
        language_label=translator.locale_label(snapshot["preferred_language"]),
        currency_label=translator.currency_label(snapshot["preferred_currency"]),
    )
