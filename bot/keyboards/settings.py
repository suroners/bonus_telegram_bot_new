from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bonus_telegram_bot.services.settings_service import TelegramSettingsService


def settings_keyboard(snapshot, translator):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(translator.t("settings.button.language"), callback_data="settings:language"),
                InlineKeyboardButton(translator.t("settings.button.currency"), callback_data="settings:currency"),
            ],
            [
                InlineKeyboardButton(
                    translator.settings_toggle_label("notifications", snapshot["notify_enabled"]),
                    callback_data="settings:toggle:notify",
                )
            ],
            [
                InlineKeyboardButton(
                    translator.settings_toggle_label("crypto", snapshot["receive_crypto_bonuses"]),
                    callback_data="settings:toggle:crypto",
                )
            ],
            [
                InlineKeyboardButton(
                    translator.settings_toggle_label("freespins", snapshot["receive_freespins"]),
                    callback_data="settings:toggle:freespins",
                )
            ],
            [
                InlineKeyboardButton(
                    translator.settings_toggle_label("deposit", snapshot["receive_deposit_bonuses"]),
                    callback_data="settings:toggle:deposit",
                )
            ],
        ]
    )


def language_keyboard(translator, current_language):
    rows = []
    for locale_code in TelegramSettingsService.supported_languages():
        label = translator.locale_label(locale_code)
        if locale_code == current_language:
            label = "✓ %s" % label
        rows.append([InlineKeyboardButton(label, callback_data="settings:set_language:%s" % locale_code)])
    rows.append([InlineKeyboardButton(translator.t("common.back"), callback_data="settings:back")])
    return InlineKeyboardMarkup(rows)


def currency_keyboard(translator, current_currency):
    rows = []
    unset_label = translator.t("settings.currency.unset")
    if not current_currency:
        unset_label = "✓ %s" % unset_label
    rows.append([InlineKeyboardButton(unset_label, callback_data="settings:set_currency:none")])
    for currency_code in TelegramSettingsService.supported_currencies():
        label = currency_code
        if currency_code == (current_currency or "").upper():
            label = "✓ %s" % label
        rows.append([InlineKeyboardButton(label, callback_data="settings:set_currency:%s" % currency_code.lower())])
    rows.append([InlineKeyboardButton(translator.t("common.back"), callback_data="settings:back")])
    return InlineKeyboardMarkup(rows)
