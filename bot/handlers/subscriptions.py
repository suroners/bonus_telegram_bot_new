from telegram import Update
from telegram.ext import ContextTypes

from bonus_telegram_bot.bot.utils.global_nav import global_navigation_keyboard
from bonus_telegram_bot.i18n import TelegramI18nService
from bonus_telegram_bot.services.subscription_service import SubscriptionService
from bonus_telegram_bot.services.user_service import TelegramUserService


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    casino_name = " ".join(context.args).strip()
    if not casino_name:
        await update.effective_message.reply_text(
            translator.t("subscriptions.usage.subscribe"),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    result = await SubscriptionService.subscribe(update.effective_user.id, casino_name)
    await update.effective_message.reply_text(
        _subscription_message(translator, result),
        reply_markup=global_navigation_keyboard(translator),
    )


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await TelegramUserService.register(update.effective_user)
    translator = await TelegramI18nService.for_user(
        update.effective_user.id,
        getattr(update.effective_user, "language_code", None),
    )
    casino_name = " ".join(context.args).strip()
    if not casino_name:
        await update.effective_message.reply_text(
            translator.t("subscriptions.usage.unsubscribe"),
            reply_markup=global_navigation_keyboard(translator),
        )
        return
    result = await SubscriptionService.unsubscribe(update.effective_user.id, casino_name)
    await update.effective_message.reply_text(
        _subscription_message(translator, result),
        reply_markup=global_navigation_keyboard(translator),
    )


def _subscription_message(translator, result):
    key = "subscriptions.result.%s" % result["code"]
    if "casino" in result:
        return translator.t(key, casino=result["casino"])
    return translator.t(key)
