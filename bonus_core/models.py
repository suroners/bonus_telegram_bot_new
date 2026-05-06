from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Geo(TimeStampedModel):
    source_id = models.IntegerField(null=True, blank=True, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    is_regulated = models.BooleanField(default=False)
    sort = models.IntegerField(default=0)
    has_ppc = models.BooleanField(default=False)
    meta = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "name"]

    def __str__(self):
        return "%s (%s)" % (self.name, self.code)


class Vertical(TimeStampedModel):
    source_id = models.IntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Casino(TimeStampedModel):
    source_id = models.IntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=180)
    slug = models.CharField(max_length=180, blank=True, default="")
    type = models.CharField(max_length=80, blank=True, default="")
    release_date = models.DateField(null=True, blank=True)
    logo_url = models.URLField(blank=True, default="")
    aggregator_type = models.CharField(max_length=120, blank=True, default="")
    aggregator_source = models.CharField(max_length=255, blank=True, default="")
    regulated_option = models.CharField(max_length=80, blank=True, default="")
    crypto_friendly_option = models.CharField(max_length=80, blank=True, default="")
    my_brand = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    verticals = models.ManyToManyField(Vertical, blank=True, related_name="casinos")

    class Meta:
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["name"], name="bonus_core_casino_name_idx"),
            models.Index(fields=["priority"], name="bonus_core_casino_priority_idx"),
        ]

    def __str__(self):
        return self.name


class CasinoLocation(TimeStampedModel):
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="locations")
    geo = models.ForeignKey(Geo, on_delete=models.CASCADE, related_name="casino_locations")
    brand_traffic_share = models.IntegerField(default=0)
    location_id = models.IntegerField(null=True, blank=True)
    total_share_of_traffic = models.IntegerField(default=0)
    market_share = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    position = models.IntegerField(null=True, blank=True)
    websites_found = models.IntegerField(default=0)

    class Meta:
        unique_together = ("casino", "geo")
        ordering = ["geo__sort", "position"]

    def __str__(self):
        return "%s - %s" % (self.casino, self.geo)


class CasinoBonusPage(TimeStampedModel):
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="bonus_pages")
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonus_pages")
    source_code = models.CharField(max_length=32, blank=True, default="")
    url = models.URLField(max_length=1000)
    notes = models.TextField(blank=True, default="")
    affiliate_url = models.URLField(max_length=1000, blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    class Meta:
        ordering = ["-priority", "casino__name", "geo__sort", "url"]
        indexes = [
            models.Index(fields=["source_code"], name="bc_bpage_source_idx"),
            models.Index(fields=["is_active"], name="bc_bpage_active_idx"),
            models.Index(fields=["priority"], name="bc_bpage_priority_idx"),
        ]
        unique_together = ("casino", "geo", "source_code", "url")

    def __str__(self):
        geo_code = self.geo.code if self.geo_id else "default"
        return "%s %s %s" % (self.casino, geo_code, self.url)


class AffiliateAccount(TimeStampedModel):
    casino = models.OneToOneField(Casino, on_delete=models.CASCADE, related_name="affiliate_account")
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    affiliate_id = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return "Affiliate account for %s" % self.casino


class AffiliateMedia(TimeStampedModel):
    affiliate = models.ForeignKey(AffiliateAccount, on_delete=models.CASCADE, related_name="media")
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="affiliate_media")
    url = models.URLField(max_length=1000)

    class Meta:
        verbose_name_plural = "Affiliate media"

    def __str__(self):
        return self.url


class ScraperProxy(TimeStampedModel):
    name = models.CharField(max_length=120, blank=True, default="")
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="scraper_proxies")
    server = models.CharField(max_length=500)
    username = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-priority", "id"]
        indexes = [
            models.Index(fields=["geo", "is_active"], name="bc_sproxy_geo_active_idx"),
            models.Index(fields=["is_active", "priority"], name="bc_sproxy_active_prio_idx"),
        ]

    def __str__(self):
        geo_code = self.geo.code if self.geo_id else "default"
        return "%s proxy %s" % (geo_code, self.server)


class GameProvider(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    logo_url = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Game(TimeStampedModel):
    provider = models.ForeignKey(GameProvider, on_delete=models.CASCADE, related_name="games")
    name = models.CharField(max_length=180)
    type = models.CharField(max_length=120, blank=True, default="")
    rtp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    logo_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = ("provider", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScrapeStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"


class ScrapedHistory(TimeStampedModel):
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="scrape_history")
    bonus_page = models.ForeignKey(
        CasinoBonusPage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scrape_history",
    )
    url = models.URLField(max_length=1000)
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="scrape_history")
    scraped_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=ScrapeStatus.choices)
    error_message = models.TextField(blank=True, default="")
    raw_html = models.TextField(blank=True, default="")
    final_url = models.URLField(max_length=1000, blank=True, default="")
    aggregator_type = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        ordering = ["-scraped_at"]
        indexes = [
            models.Index(fields=["status", "scraped_at"], name="bonus_core_scraped_status_idx"),
            models.Index(fields=["url"], name="bonus_core_scraped_url_idx"),
        ]

    def __str__(self):
        return "%s %s %s" % (self.casino, self.status, self.scraped_at)


class QueueStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    DONE = "DONE", "Done"
    FAILED = "FAILED", "Failed"


class AIParsingQueue(TimeStampedModel):
    scraped_history = models.ForeignKey(
        ScrapedHistory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_queue_items",
    )
    scraped_history_id_external = models.IntegerField(null=True, blank=True)
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="ai_queue_items")
    url = models.URLField(max_length=1000)
    raw_html = models.TextField()
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="ai_queue_items")
    status = models.CharField(max_length=20, choices=QueueStatus.choices, default=QueueStatus.PENDING)
    error_message = models.TextField(blank=True, default="")
    traceback = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="bonus_core_aiparse_status_idx"),
        ]

    def __str__(self):
        return "%s %s" % (self.casino, self.status)


class AIProviderConfig(TimeStampedModel):
    PROVIDER_OPENAI = "openai"
    PROVIDER_GOOGLE = "google"
    PROVIDER_ANTHROPIC = "anthropic"
    PROVIDER_SCRIPT = "script"

    PROVIDER_CHOICES = (
        (PROVIDER_OPENAI, "OpenAI"),
        (PROVIDER_GOOGLE, "Google Gemini"),
        (PROVIDER_ANTHROPIC, "Anthropic"),
        (PROVIDER_SCRIPT, "Script Parser"),
    )

    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    model = models.CharField(max_length=120)
    api_key = models.CharField(max_length=500, blank=True, default="")
    enabled = models.BooleanField(default=False)
    priority = models.IntegerField(default=100)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["priority", "provider"]

    def __str__(self):
        return "%s:%s" % (self.provider, self.model)


class ReferenceRunStatus(models.TextChoices):
    RUNNING = "RUNNING", "Running"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class ParserReferenceRun(TimeStampedModel):
    source_scraped_history = models.ForeignKey(
        ScrapedHistory,
        on_delete=models.CASCADE,
        related_name="parser_reference_runs",
    )
    provider = models.CharField(max_length=30, choices=AIProviderConfig.PROVIDER_CHOICES)
    model = models.CharField(max_length=120, blank=True, default="")
    label = models.CharField(max_length=120, blank=True, default="baseline")
    status = models.CharField(max_length=20, choices=ReferenceRunStatus.choices, default=ReferenceRunStatus.RUNNING)
    bonus_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_scraped_history", "provider", "label"],
                name="bonus_core_pref_run_unique_idx",
            )
        ]
        indexes = [
            models.Index(fields=["provider", "label", "status"], name="bc_pref_run_state_idx"),
        ]

    def __str__(self):
        return "%s %s %s" % (self.source_scraped_history_id, self.provider, self.label)


class Bonus(TimeStampedModel):
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="bonuses")
    game = models.ForeignKey(Game, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonuses")
    provider = models.ForeignKey(GameProvider, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonuses")
    source_scraped_history = models.ForeignKey(
        ScrapedHistory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bonuses",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    type = models.CharField(max_length=120, blank=True, default="")
    wagering_requirement = models.CharField(max_length=255, blank=True, default="")
    min_deposit = models.CharField(max_length=120, blank=True, default="")
    max_bonus = models.CharField(max_length=120, blank=True, default="")
    currency = models.CharField(max_length=30, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="bonuses")
    bonus_url = models.URLField(max_length=1000, blank=True, default="")
    is_auto = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-priority", "-casino__priority", "-created_at"]
        indexes = [
            models.Index(fields=["is_active", "is_approved"], name="bonus_core_bonus_state_idx"),
            models.Index(fields=["priority", "created_at"], name="bonus_core_bonus_rank_idx"),
            models.Index(fields=["type"], name="bonus_core_bonus_type_idx"),
        ]

    def __str__(self):
        return "%s - %s" % (self.casino, self.title)


class TelegramUser(TimeStampedModel):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    geo = models.ForeignKey(Geo, null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_users")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return str(self.telegram_id)


class UserSettings(TimeStampedModel):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE, related_name="settings")
    notify_enabled = models.BooleanField(default=True)
    preferred_currency = models.CharField(max_length=30, null=True, blank=True)
    preferred_language = models.CharField(max_length=16, default="en")
    receive_crypto_bonuses = models.BooleanField(default=True)
    receive_freespins = models.BooleanField(default=True)
    receive_deposit_bonuses = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "User settings"

    def __str__(self):
        return "Settings for %s" % self.user


class UserCasinoSubscription(TimeStampedModel):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="casino_subscriptions")
    casino = models.ForeignKey(Casino, on_delete=models.CASCADE, related_name="telegram_subscribers")

    class Meta:
        unique_together = ("user", "casino")
        ordering = ["-created_at"]

    def __str__(self):
        return "%s -> %s" % (self.user, self.casino)


class NotificationStatus(models.TextChoices):
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class NotificationHistory(TimeStampedModel):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="notification_history")
    bonus = models.ForeignKey(Bonus, null=True, blank=True, on_delete=models.SET_NULL, related_name="notification_history")
    bonus_reference_id = models.IntegerField()
    casino = models.ForeignKey(Casino, null=True, blank=True, on_delete=models.SET_NULL, related_name="notification_history")
    sent_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=NotificationStatus.choices)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "bonus_reference_id")
        ordering = ["-sent_at"]
        verbose_name_plural = "Notification history"

    def __str__(self):
        return "%s %s %s" % (self.user, self.bonus_reference_id, self.status)
