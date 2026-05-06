from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def geo_keyboard(page_data, translator):
    rows = []
    geos = page_data["geos"]
    for index in range(0, len(geos), 2):
        row = []
        for geo in geos[index : index + 2]:
            row.append(
                InlineKeyboardButton(
                    "%s (%s)" % (geo["name"], geo["code"].upper()),
                    callback_data="geo:set:%s" % geo["code"],
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                translator.t("geo.search.button"),
                callback_data="geo:search:%s" % page_data["page"],
            )
        ]
    )

    nav = []
    if page_data["has_prev"]:
        nav.append(
            InlineKeyboardButton(
                translator.t("geo.nav.prev"),
                callback_data="geo:page:%s" % (page_data["page"] - 1),
            )
        )
    if page_data["has_next"]:
        nav.append(
            InlineKeyboardButton(
                translator.t("geo.nav.next"),
                callback_data="geo:page:%s" % (page_data["page"] + 1),
            )
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def geo_search_prompt_keyboard(translator, back_page):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    translator.t("geo.search.back_to_list"),
                    callback_data="geo:back:%s" % back_page,
                )
            ]
        ]
    )


def geo_search_results_keyboard(geos, translator, back_page):
    rows = []
    for index in range(0, len(geos), 2):
        row = []
        for geo in geos[index : index + 2]:
            row.append(
                InlineKeyboardButton(
                    "%s (%s)" % (geo["name"], geo["code"].upper()),
                    callback_data="geo:set:%s" % geo["code"],
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                translator.t("geo.search.again"),
                callback_data="geo:search:%s" % back_page,
            ),
            InlineKeyboardButton(
                translator.t("geo.search.back_to_list"),
                callback_data="geo:back:%s" % back_page,
            ),
        ]
    )
    return InlineKeyboardMarkup(rows)
