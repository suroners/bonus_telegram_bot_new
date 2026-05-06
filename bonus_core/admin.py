import re
from html import escape

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme

from bonus_core.models import (
    AIParsingQueue,
    AIProviderConfig,
    AffiliateAccount,
    AffiliateMedia,
    Bonus,
    Casino,
    CasinoBonusPage,
    CasinoLocation,
    Game,
    GameProvider,
    Geo,
    NotificationHistory,
    ParserReferenceRun,
    ScraperProxy,
    ScrapedHistory,
    TelegramUser,
    UserCasinoSubscription,
    UserSettings,
    Vertical,
)


@admin.register(Geo)
class GeoAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "is_regulated", "has_ppc", "sort", "is_active")
    list_filter = ("is_regulated", "has_ppc", "is_active")
    search_fields = ("code", "name")


@admin.register(Casino)
class CasinoAdmin(admin.ModelAdmin):
    list_display = ("name", "source_id", "priority", "aggregator_type", "my_brand")
    list_filter = ("my_brand", "aggregator_type")
    search_fields = ("name", "slug")
    filter_horizontal = ("verticals",)


@admin.register(CasinoBonusPage)
class CasinoBonusPageAdmin(admin.ModelAdmin):
    list_display = ("casino", "geo", "source_code", "is_default", "is_active", "priority", "has_affiliate_url")
    list_filter = ("is_default", "is_active", "geo")
    search_fields = ("casino__name", "url", "affiliate_url", "source_code")

    def has_affiliate_url(self, obj):
        return bool(obj.affiliate_url)

    has_affiliate_url.boolean = True


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    change_list_template = "admin/bonus_core/bonus/change_list.html"
    list_display = (
        "title",
        "casino",
        "geo",
        "type",
        "parser_provider",
        "is_reference",
        "approval_button",
        "is_active",
        "priority",
        "created_at",
    )
    list_filter = ("is_approved", "is_active", "type", "geo")
    search_fields = ("title", "description", "casino__name")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/toggle-approval/",
                self.admin_site.admin_view(self.toggle_approval_view),
                name="bonus_core_bonus_toggle_approval",
            )
        ]
        return custom_urls + urls

    def parser_provider(self, obj):
        return obj.raw_payload.get("parser_provider", "")

    def is_reference(self, obj):
        return bool(obj.raw_payload.get("parser_is_reference"))

    is_reference.boolean = True

    def toggle_approval_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])

        bonus = self.get_object(request, object_id)
        if bonus is None:
            raise Http404("Bonus does not exist.")
        if not self.has_change_permission(request, bonus):
            raise PermissionDenied

        bonus.is_approved = not bonus.is_approved
        bonus.save(update_fields=["is_approved", "updated_at"])
        self.message_user(
            request,
            'Bonus "%s" is now %s.' % (bonus.title, "approved" if bonus.is_approved else "unapproved"),
        )
        next_url = request.POST.get("next") or reverse("admin:bonus_core_bonus_changelist")
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = reverse("admin:bonus_core_bonus_changelist")
        return redirect(next_url)

    def approval_button(self, obj):
        label = "Unapprove" if obj.is_approved else "Approve"
        background = "#79aec8" if obj.is_approved else "#417690"
        form_id = "bonus-approval-form-%s" % obj.pk
        return format_html(
            """
            <button
                type="submit"
                form="{form_id}"
                style="background:{background};border:1px solid {background};border-radius:6px;color:#fff;cursor:pointer;font-weight:700;padding:6px 10px;white-space:nowrap;"
            >
                {label}
            </button>
            """,
            form_id=form_id,
            background=background,
            label=label,
        )

    approval_button.short_description = "Is approved"
    approval_button.admin_order_field = "is_approved"


admin.site.register(Vertical)
admin.site.register(CasinoLocation)
admin.site.register(AffiliateAccount)
admin.site.register(AffiliateMedia)


@admin.register(ScraperProxy)
class ScraperProxyAdmin(admin.ModelAdmin):
    list_display = ("name", "geo", "server", "is_active", "priority", "updated_at")
    list_filter = ("is_active", "geo")
    search_fields = ("name", "server", "geo__code", "geo__name")


@admin.register(ParserReferenceRun)
class ParserReferenceRunAdmin(admin.ModelAdmin):
    list_display = ("source_scraped_history", "provider", "label", "status", "bonus_count", "model", "updated_at")
    list_filter = ("provider", "label", "status")
    search_fields = ("source_scraped_history__casino__name", "source_scraped_history__url", "model", "error_message")


@admin.register(GameProvider)
class GameProviderAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    search_fields = ("name", "provider__name")


@admin.register(ScrapedHistory)
class ScrapedHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "casino", "geo", "status", "scraped_at", "aggregator_type", "final_url")
    list_filter = ("status", "geo", "aggregator_type")
    search_fields = ("casino__name", "url", "final_url", "error_message", "aggregator_type")
    readonly_fields = ("rendered_page_preview", "created_at", "updated_at")
    fields = (
        "rendered_page_preview",
        "casino",
        "bonus_page",
        "geo",
        "status",
        "scraped_at",
        "url",
        "final_url",
        "aggregator_type",
        "error_message",
        "raw_html",
        "created_at",
        "updated_at",
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="bonus_core_scrapedhistory_preview",
            )
        ]
        return custom_urls + urls

    def rendered_page_preview(self, obj):
        if not obj or not obj.pk:
            return "Save this scraped history before previewing it."

        preview_url = reverse("admin:bonus_core_scrapedhistory_preview", args=[obj.pk])
        live_url = obj.final_url or obj.url
        web_input_id = "scraped-preview-web-%s" % obj.pk
        mobile_input_id = "scraped-preview-mobile-%s" % obj.pk
        tab_name = "scraped-preview-tab-%s" % obj.pk

        return format_html(
            """
            <style>
                .scraped-preview-actions {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                    margin: 0 0 12px;
                }}
                .scraped-preview-actions a,
                .scraped-preview-tabs label {{
                    border: 1px solid #417690;
                    border-radius: 6px;
                    color: #264b5d;
                    display: inline-flex;
                    font-weight: 700;
                    padding: 8px 11px;
                    text-decoration: none;
                }}
                .scraped-preview-tabs input {{
                    height: 1px;
                    opacity: 0;
                    position: absolute;
                    width: 1px;
                }}
                .scraped-preview-tabs label {{
                    background: #fff;
                    cursor: pointer;
                    margin: 0 6px 12px 0;
                }}
                #{mobile_input_id}:checked ~ .scraped-preview-labels label[for="{mobile_input_id}"],
                #{web_input_id}:checked ~ .scraped-preview-labels label[for="{web_input_id}"] {{
                    background: #417690;
                    color: #fff;
                }}
                .scraped-preview-panel {{
                    display: none;
                    overflow: auto;
                    max-width: 100%;
                }}
                #{mobile_input_id}:checked ~ .scraped-preview-panels .scraped-preview-mobile,
                #{web_input_id}:checked ~ .scraped-preview-panels .scraped-preview-web {{
                    display: block;
                }}
                .scraped-preview-frame {{
                    background: #fff;
                    border: 1px solid #b7c4c9;
                    border-radius: 6px;
                    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
                }}
                .scraped-preview-mobile-frame {{
                    height: 844px;
                    max-width: 100%;
                    width: 390px;
                }}
                .scraped-preview-web-frame {{
                    height: 720px;
                    min-width: 900px;
                    width: 100%;
                }}
                .scraped-preview-note {{
                    color: #666;
                    margin: 0 0 10px;
                }}
            </style>
            <div class="scraped-preview-actions">
                <a href="{live_url}" target="_blank" rel="noopener noreferrer">Open final URL</a>
                <a href="{preview_url}" target="_blank" rel="noopener noreferrer">Open raw preview</a>
            </div>
            <p class="scraped-preview-note">
                Mobile preview is selected by default. Both previews use the stored raw HTML from this scrape.
            </p>
            <div class="scraped-preview-tabs">
                <input id="{mobile_input_id}" name="{tab_name}" type="radio" checked>
                <input id="{web_input_id}" name="{tab_name}" type="radio">
                <div class="scraped-preview-labels">
                    <label for="{mobile_input_id}">Mobile</label>
                    <label for="{web_input_id}">Web</label>
                </div>
                <div class="scraped-preview-panels">
                    <div class="scraped-preview-panel scraped-preview-mobile">
                        <iframe
                            class="scraped-preview-frame scraped-preview-mobile-frame"
                            src="{preview_url}"
                            title="Mobile rendered page preview"
                            sandbox="allow-scripts allow-forms"
                        ></iframe>
                    </div>
                    <div class="scraped-preview-panel scraped-preview-web">
                        <iframe
                            class="scraped-preview-frame scraped-preview-web-frame"
                            src="{preview_url}"
                            title="Web rendered page preview"
                            sandbox="allow-scripts allow-forms"
                        ></iframe>
                    </div>
                </div>
            </div>
            """,
            live_url=live_url,
            preview_url=preview_url,
            mobile_input_id=mobile_input_id,
            web_input_id=web_input_id,
            tab_name=tab_name,
        )

    rendered_page_preview.short_description = "Rendered page preview"

    def preview_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404("Scraped history does not exist.")

        response = HttpResponse(
            self._html_with_base(obj.raw_html, obj.final_url or obj.url),
            content_type="text/html; charset=utf-8",
        )
        response["Content-Security-Policy"] = (
            "sandbox allow-scripts allow-forms; "
            "default-src * data: blob: 'unsafe-inline' 'unsafe-eval'; "
            "img-src * data: blob:; "
            "media-src * data: blob:; "
            "style-src * 'unsafe-inline'; "
            "script-src * 'unsafe-inline' 'unsafe-eval'; "
            "connect-src * data: blob:; "
            "frame-src * data: blob:;"
        )
        response["Referrer-Policy"] = "no-referrer"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "SAMEORIGIN"
        return response

    def _html_with_base(self, raw_html, base_url):
        raw_html = raw_html or ""
        base_tag = ""
        if base_url:
            base_tag = '<base href="%s">' % escape(base_url, quote=True)

        if not raw_html.strip():
            return (
                "<!doctype html><html><head>%s</head>"
                "<body><p>No raw HTML was stored for this scrape.</p></body></html>"
            ) % base_tag

        if base_tag and re.search(r"<head(?:\s[^>]*)?>", raw_html, flags=re.IGNORECASE):
            return re.sub(
                r"(<head(?:\s[^>]*)?>)",
                r"\1\n%s" % base_tag,
                raw_html,
                count=1,
                flags=re.IGNORECASE,
            )

        if base_tag and re.search(r"<html(?:\s[^>]*)?>", raw_html, flags=re.IGNORECASE):
            return re.sub(
                r"(<html(?:\s[^>]*)?>)",
                r"\1<head>%s</head>" % base_tag,
                raw_html,
                count=1,
                flags=re.IGNORECASE,
            )

        return "<!doctype html><html><head>%s</head><body>%s</body></html>" % (base_tag, raw_html)


admin.site.register(AIParsingQueue)
admin.site.register(AIProviderConfig)
admin.site.register(TelegramUser)
admin.site.register(UserSettings)
admin.site.register(UserCasinoSubscription)
admin.site.register(NotificationHistory)
