from django.apps import AppConfig


class BonusCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bonus_core"
    verbose_name = "Bonus core"

    def ready(self):
        import bonus_core.signals  # noqa: F401
