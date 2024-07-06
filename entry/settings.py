import os
from pathlib import Path

from environ import environ
from ovinc_client.core.logger import get_logging_config_dict
from ovinc_client.core.utils import getenv_or_raise, strtobool

# Base Dir
BASE_DIR = Path(__file__).resolve().parent.parent

# Env
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# DEBUG
DEBUG = strtobool(os.getenv("DEBUG", "False"))

# APP_CODE & SECRET
APP_CODE = getenv_or_raise("APP_CODE")
APP_SECRET = getenv_or_raise("APP_SECRET")
SECRET_KEY = getenv_or_raise("APP_SECRET")

# Hosts
ALLOWED_HOSTS = [getenv_or_raise("BACKEND_HOST")]
CORS_ALLOW_CREDENTIALS = strtobool(os.getenv("CORS_ALLOW_CREDENTIALS", "True"))
CORS_ORIGIN_WHITELIST = [getenv_or_raise("FRONTEND_URL")]
CSRF_TRUSTED_ORIGINS = [getenv_or_raise("FRONTEND_URL")]
FRONTEND_URL = getenv_or_raise("FRONTEND_URL")

# APPs
INSTALLED_APPS = [
    "daphne",
    "simpleui",
    "corsheaders",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "sslserver",
    "ovinc_client.account",
    "ovinc_client.trace",
    "apps.cel",
    "apps.chat",
    "apps.home",
    "apps.cos",
    "apps.wallet",
]

# MIDDLEWARE
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "ovinc_client.core.middlewares.CSRFExemptMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "ovinc_client.core.middlewares.SQLDebugMiddleware",
]
if DEBUG:
    MIDDLEWARE += ["pyinstrument.middleware.ProfilerMiddleware"]
    PYINSTRUMENT_PROFILE_DIR = ".report"
if not DEBUG:
    MIDDLEWARE += ["ovinc_client.core.middlewares.UnHandleExceptionMiddleware"]

# Urls
ROOT_URLCONF = "entry.urls"

# TEMPLATES
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

# DB and Cache
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": getenv_or_raise("DB_NAME"),
        "USER": getenv_or_raise("DB_USER"),
        "PASSWORD": getenv_or_raise("DB_PASSWORD"),
        "HOST": getenv_or_raise("DB_HOST"),
        "PORT": int(getenv_or_raise("DB_PORT")),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", str(60 * 60))),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REDIS_HOST = getenv_or_raise("REDIS_HOST")
REDIS_PORT = int(getenv_or_raise("REDIS_PORT"))
REDIS_PASSWORD = getenv_or_raise("REDIS_PASSWORD")
REDIS_DB = int(getenv_or_raise("REDIS_DB"))
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
    }
}

# ASGI
ASGI_APPLICATION = "entry.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            ],
        },
    },
}

# Auth
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# International
LANGUAGE_CODE = os.getenv("DEFAULT_LANGUAGE", "zh-hans")
TIME_ZONE = os.getenv("DEFAULT_TIME_ZONE", "Asia/Shanghai")
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = (("zh-hans", "中文简体"), ("en", "English"))
LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

# Static
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "staticfiles")]

# Session
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", f"{'dev-' if DEBUG else ''}{APP_CODE}-sessionid")
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN")

# Log
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOGGING = get_logging_config_dict(LOG_LEVEL, LOG_DIR)

# rest_framework
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["ovinc_client.core.renderers.APIRenderer"],
    "DEFAULT_PAGINATION_CLASS": "ovinc_client.core.paginations.NumPagination",
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DEFAULT_THROTTLE_RATES": {},
    "EXCEPTION_HANDLER": "ovinc_client.core.exceptions.exception_handler",
    "UNAUTHENTICATED_USER": "ovinc_client.account.models.CustomAnonymousUser",
    "DEFAULT_AUTHENTICATION_CLASSES": ["ovinc_client.core.auth.LoginRequiredAuthenticate"],
}

# User
AUTH_USER_MODEL = "account.User"

# Celery
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_ACCEPT_CONTENT = ["pickle", "json"]
BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# APM
ENABLE_TRACE = strtobool(os.getenv("ENABLE_TRACE", "False"))
SERVICE_NAME = os.getenv("SERVICE_NAME", APP_CODE)
OTLP_HOST = os.getenv("OTLP_HOST", "http://127.0.0.1:4317")
OTLP_TOKEN = os.getenv("OTLP_TOKEN", "")

# RUM
RUM_ID = os.getenv("RUM_ID", "")
RUM_HOST = os.getenv("RUM_HOST", "https://rumt-zh.com")

# OVINC
OVINC_API_DOMAIN = getenv_or_raise("OVINC_API_DOMAIN")
OVINC_API_RECORD_LOG = strtobool(os.getenv("OVINC_API_RECORD_LOG", "True"))

# OpenAI
OPENAI_HTTP_PROXY_URL = os.getenv("OPENAI_HTTP_PROXY_URL")
OPENAI_API_KEY = os.getenv("DEFAULT_OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("DEFAULT_OPENAI_API_BASE")
OPENAI_MAX_ALLOWED_TOKENS = int(os.getenv("OPENAI_MAX_ALLOWED_TOKENS", "4000"))
OPENAI_PRE_CHECK_TIMEOUT = int(os.getenv("OPENAI_PRE_CHECK_TIMEOUT", "600"))

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# QCLOUD
QCLOUD_SECRET_ID = os.getenv("QCLOUD_SECRET_ID")
QCLOUD_SECRET_KEY = os.getenv("QCLOUD_SECRET_KEY")

# Hunyuan
HUNYUAN_IMAGE_API_REGION = os.getenv("HUNYUAN_IMAGE_API_REGION", "ap-guangzhou")
HUNYUAN_IMAGE_JOB_INTERVAL = int(os.getenv("HUNYUAN_IMAGE_JOB_INTERVAL", "5"))
HUNYUAN_IMAGE_JOB_TIMEOUT = int(os.getenv("HUNYUAN_IMAGE_JOB_TIMEOUT", "600"))

# Captcha
CAPTCHA_TCLOUD_ID = os.getenv("CAPTCHA_TCLOUD_ID", QCLOUD_SECRET_ID)
CAPTCHA_TCLOUD_KEY = os.getenv("CAPTCHA_TCLOUD_KEY", QCLOUD_SECRET_KEY)
CAPTCHA_ENABLED = strtobool(os.getenv("CAPTCHA_ENABLED", "False"))
CAPTCHA_APP_ID = int(os.getenv("CAPTCHA_APP_ID", str(0)))
CAPTCHA_APP_SECRET = os.getenv("CAPTCHA_APP_SECRET", "")
CAPTCHA_APP_INFO_TIMEOUT = int(os.getenv("CAPTCHA_APP_INFO_TIMEOUT", str(60 * 10)))

# COS
QCLOUD_COS_URL = os.getenv("QCLOUD_COS_URL")
QCLOUD_COS_BUCKET = os.getenv("QCLOUD_COS_BUCKET")
QCLOUD_COS_REGION = os.getenv("QCLOUD_COS_REGION", "ap-beijing")
QCLOUD_COS_SECRET_ID = os.getenv("QCLOUD_COS_SECRET_ID", QCLOUD_SECRET_ID)
QCLOUD_COS_SECRET_KEY = os.getenv("QCLOUD_COS_SECRET_KEY", QCLOUD_SECRET_KEY)
QCLOUD_COS_RANDOM_KEY_LENGTH = int(os.getenv("QCLOUD_COS_RANDOM_KEY_LENGTH", "10"))
QCLOUD_KEY_DUPLICATE_TIMEOUT = int(os.getenv("QCLOUD_KEY_DUPLICATE_TIMEOUT", str(60 * 60 * 24)))
QCLOUD_COS_IMAGE_STYLE = os.getenv("QCLOUD_COS_IMAGE_STYLE", "imageMogr2/quality/80/format/webp/interlace/1")

# STS
QCLOUD_API_DOMAIN_TMPL = os.getenv("QCLOUD_API_DOMAIN_TMPL", "{}.tencentcloudapi.com")
QCLOUD_API_SCHEME = os.getenv("QCLOUD_API_SCHEME", "https")
QCLOUD_STS_EXPIRE_TIME = int(os.getenv("QCLOUD_STS_EXPIRE_TIME", str(60 * 10)))

# Baidu Qianfan
QIANFAN_ACCESS_KEY = os.getenv("QIANFAN_ACCESS_KEY", "")
QIANFAN_SECRET_KEY = os.getenv("QIANFAN_SECRET_KEY", "")

# Log
# this feature is removed and cannot be opened
RECORD_CHAT_CONTENT = False
CHATLOG_QUERY_DAYS = int(os.getenv("CHATLOG_QUERY_DAYS", "7"))

# IMAGE
ENABLE_IMAGE_PROXY = strtobool(os.getenv("ENABLE_IMAGE_PROXY", "False"))

# Kimi
KIMI_API_KEY = os.getenv("KIMI_API_KEY")
KIMI_API_BASE_URL = os.getenv("KIMI_API_BASE_URL")

# File
ENABLE_FILE_UPLOAD = strtobool(os.getenv("ENABLE_FILE_UPLOAD", "False"))
LOAD_FILE_TIMEOUT = int(os.getenv("LOAD_FILE_TIMEOUT", "60"))

# Tool
CHATGPT_TOOLS_ENABLED = strtobool(os.getenv("CHATGPT_TOOLS_ENABLED", "False"))

# WXPay
WXPAY_ENABLED = strtobool(os.getenv("WXPAY_ENABLED", "False"))
WXPAY_PRIVATE_KEY_SERIAL_NO = os.getenv("WXPAY_PRIVATE_KEY_SERIAL_NO", "")
WXPAY_PRIVATE_KEY_PATH = os.getenv("WXPAY_PRIVATE_KEY_PATH", "")
WXPAY_AUTH_TYPE = os.getenv("WXPAY_AUTH_TYPE", "WECHATPAY2-SHA256-RSA2048")
WXPAY_APP_ID = os.getenv("WXPAY_APP_ID", "")
WXPAY_MCHID = os.getenv("WXPAY_MCHID", "")
WXPAY_API_BASE_URL = os.getenv("WXPAY_API_BASE_URL", "https://api.mch.weixin.qq.com")
WXPAY_API_V3_KEY = os.getenv("WXPAY_API_V3_KEY", "")
WXPAY_CERT_TIMEOUT = int(os.getenv("WXPAY_CERT_TIMEOUT", str(60 * 60 * 24 * 7)))
WXPAY_TIME_FORMAT = os.getenv("WXPAY_TIME_FORMAT", "%Y-%m-%dT%H:%M:%S%z")
WXPAY_NOTIFY_URL = os.getenv("WXPAY_NOTIFY_URL", "")
WXPAY_UNIT_TRANS = int(os.getenv("WXPAY_UNIT_TRANS", "100"))
WXPAY_UNIT = os.getenv("WXPAY_UNIT", "")
WXPAY_ORDER_TIMEOUT = int(os.getenv("WXPAY_ORDER_TIMEOUT", str(60 * 10)))
WXPAY_SUPPORT_FAPIAO = strtobool(os.getenv("WXPAY_SUPPORT_FAPIAO", "False"))

# Doubao
DOUBAO_API_BASE_URL = os.getenv("DOUBAO_API_BASE_URL", "")
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "")
