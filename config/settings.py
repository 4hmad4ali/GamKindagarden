"""Settings for the GAAM Kindergarten Management System."""

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_flag(name, default=False):
    """Read a conventional true/false environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    """Read a comma-separated environment variable."""
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in the environment or .env file.")

DEBUG = env_flag("DEBUG", default=False)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1" if DEBUG else "",
)
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set when DEBUG is False.")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "accounts",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.RoleAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

# Supports both this project's existing DATABASE_* names and Railway's MySQL
# service variables. Keep all real values in Railway Variables, never in Git.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQLDATABASE", os.getenv("MYSQL_DATABASE", os.getenv("DATABASE_NAME", ""))),
        "USER": os.getenv("MYSQLUSER", os.getenv("MYSQL_USER", os.getenv("DATABASE_USER", ""))),
        "PASSWORD": os.getenv("MYSQLPASSWORD", os.getenv("MYSQL_PASSWORD", os.getenv("DATABASE_PASSWORD", ""))),
        "HOST": os.getenv("MYSQLHOST", os.getenv("MYSQL_HOST", os.getenv("DATABASE_HOST", ""))),
        "PORT": os.getenv("MYSQLPORT", os.getenv("MYSQL_PORT", os.getenv("DATABASE_PORT", "3306"))),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Kabul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login_chat"
LOGIN_REDIRECT_URL = "chat_dashboard"

KINDERGARTEN_NAME = os.getenv("KINDERGARTEN_NAME", "GAAM Kindergarten")
KINDERGARTEN_ADDRESS = os.getenv("KINDERGARTEN_ADDRESS", "Microrayan 3rd District, Kabul, Afghanistan")
KINDERGARTEN_PHONE = os.getenv("KINDERGARTEN_PHONE", "0788919112")
KINDERGARTEN_EMAIL = os.getenv("KINDERGARTEN_EMAIL", "info@gaam-kindergarten.com")
KINDERGARTEN_WEBSITE = os.getenv("KINDERGARTEN_WEBSITE", "www.gaam-kindergarten.com")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_flag("SECURE_SSL_REDIRECT", default=True)
    # Enable HSTS only after HTTPS is active. Railway's generated domains and
    # properly configured custom domains are always served over HTTPS.
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_flag("SECURE_HSTS_INCLUDE_SUBDOMAINS")
    SECURE_HSTS_PRELOAD = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
