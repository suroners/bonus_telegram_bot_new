from bonus_core.models import CasinoBonusPage


class BonusLinkService:
    """Resolve the outbound URL Telegram should show for a bonus."""

    @staticmethod
    def resolve_bonus_url(bonus):
        page = BonusLinkService._page_for_bonus(bonus, affiliate_required=True)
        if page and page.affiliate_url:
            return page.affiliate_url
        if bonus.bonus_url:
            return bonus.bonus_url
        page = BonusLinkService._page_for_bonus(bonus, affiliate_required=False)
        if page:
            return page.url
        return ""

    @staticmethod
    def _page_for_bonus(bonus, affiliate_required):
        pages = CasinoBonusPage.objects.filter(casino=bonus.casino, is_active=True)
        if affiliate_required:
            pages = pages.exclude(affiliate_url="")

        if bonus.geo_id:
            page = pages.filter(geo_id=bonus.geo_id).order_by("-priority", "-updated_at").first()
            if page:
                return page
            if bonus.geo.parent_id:
                page = pages.filter(geo_id=bonus.geo.parent_id).order_by("-priority", "-updated_at").first()
                if page:
                    return page

        return pages.filter(is_default=True).order_by("-priority", "-updated_at").first()
