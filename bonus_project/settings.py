"""Shared Django settings for the casino bonus platform."""
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "bonus_core.apps.BonusCoreConfig",
    "bonus_scraping.apps.BonusScrapingConfig",
    "ai_parsing.apps.AIParsingConfig",
    "bonus_telegram_bot.apps.BonusTelegramBotConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bonus_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "bonus_project.wsgi.application"

if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "postgres"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "1800"))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_NO_GEO_MODE = os.environ.get("TELEGRAM_NO_GEO_MODE", "top_per_casino")
TELEGRAM_NO_GEO_CASINO_LIMIT = max(int(os.environ.get("TELEGRAM_NO_GEO_CASINO_LIMIT", "3")), 1)
TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT = max(int(os.environ.get("TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT", "1")), 1)
TELEGRAM_NO_GEO_CASINO_COMMAND_LIMIT = max(int(os.environ.get("TELEGRAM_NO_GEO_CASINO_COMMAND_LIMIT", "3")), 1)
SCRAPER_MICROSERVICE_URL = os.environ.get("SCRAPER_MICROSERVICE_URL", "")
API_MICROSERVICE_URL = os.environ.get("API_MICROSERVICE_URL", "")
DEFAULT_LLM_PROVIDER = os.environ.get("DEFAULT_LLM_PROVIDER", "openai")
DEFAULT_PARSER_PROVIDER = os.environ.get("DEFAULT_PARSER_PROVIDER", DEFAULT_LLM_PROVIDER)
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "60"))
SCRAPER_DEFAULT_TIMEOUT_MS = int(os.environ.get("SCRAPER_DEFAULT_TIMEOUT_MS", "60000"))
SCRAPER_HEADLESS = os.environ.get("SCRAPER_HEADLESS", "1") != "0"
PROXY_URLS = [item.strip() for item in os.environ.get("PROXY_URLS", "").split(",") if item.strip()]
GEO_PROXY_DEFAULT = os.environ.get("GEO_PROXY_DEFAULT", "")
GEO_PROXY_MAP = os.environ.get("GEO_PROXY_MAP", "")
WEBSHARE_API_TOKEN = os.environ.get("WEBSHARE_API_TOKEN", "")
WEBSHARE_PROXY_MODE = os.environ.get("WEBSHARE_PROXY_MODE", "direct")
WEBSHARE_COUNTRY_CODES = [
    item.strip().upper()
    for item in os.environ.get("WEBSHARE_COUNTRY_CODES", "").split(",")
    if item.strip()
]
PUBLIC_PROXY_LIST_URL = os.environ.get("PUBLIC_PROXY_LIST_URL") or (
    "https://api.proxyscrape.com/v4/free-proxy-list/get"
    "?request=display_proxies&protocol=http&proxy_format=protocolipport&format=text&timeout=10000"
)
PUBLIC_PROXY_IMPORT_LIMIT = int(os.environ.get("PUBLIC_PROXY_IMPORT_LIMIT", "10"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s","time":"%(asctime)s"}'
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
