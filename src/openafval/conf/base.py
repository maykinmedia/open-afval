# ruff: noqa: F403,F405
from django.utils.translation import gettext_lazy as _

from open_api_framework.conf.base import *  # noqa
from open_api_framework.conf.utils import config  # noqa

TIME_ZONE = "Europe/Amsterdam"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

#
# APPLICATIONS enabled for this project
#

INSTALLED_APPS = INSTALLED_APPS + [
    # External applications.
    "capture_tag",
    "hijack",
    "hijack.contrib.admin",
    "maykin_common",
    # Project applications.
    "openafval.accounts",
    "openafval.api",
    "openafval.utils",
]

# Remove unused/irrelevant apps added by OAF
INSTALLED_APPS.remove("django_markup")
INSTALLED_APPS.remove("csp")
INSTALLED_APPS.remove("corsheaders")
INSTALLED_APPS.remove("vng_api_common")
INSTALLED_APPS.remove("notifications_api_common")

MIDDLEWARE = MIDDLEWARE + [
    "hijack.middleware.HijackUserMiddleware",
    # NOTE: affects *all* requests, not just API calls. We can't subclass (yet) either
    # to modify the behaviour, since drf-spectacular has a bug in its `issubclass`
    # check, which is unreleased at the time of writing:
    # https://github.com/tfranzel/drf-spectacular/commit/71c7a04ee8921c01babb11fbe2938397a372dac7
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
]

# Remove unused/irrelevant middleware added by OAF
MIDDLEWARE.remove("corsheaders.middleware.CorsMiddleware")
MIDDLEWARE.remove("csp.contrib.rate_limiting.RateLimitedCSPMiddleware")

#
# LOGGING
#

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s %(module)s "
                "%(process)d %(thread)d  %(message)s"
            )
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {
            "format": "%(asctime)s %(process)d | %(thread)d | %(message)s",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "openafval.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "performance.log",
            "formatter": "performance",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
    },
    "loggers": {
        "openafval": {
            "handlers": ["project"] if not LOG_STDOUT else ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["django"] if not LOG_STDOUT else ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

#
# SECURITY settings
#

CSRF_FAILURE_VIEW = "openafval.accounts.views.csrf_failure"

#
# Custom settings
#
PROJECT_NAME = _("Open Afval")
ENABLE_ADMIN_NAV_SIDEBAR = config("ENABLE_ADMIN_NAV_SIDEBAR", default=False)

# Displaying environment information
ENVIRONMENT_LABEL = config("ENVIRONMENT_LABEL", ENVIRONMENT)
ENVIRONMENT_BACKGROUND_COLOR = config("ENVIRONMENT_BACKGROUND_COLOR", "orange")
ENVIRONMENT_FOREGROUND_COLOR = config("ENVIRONMENT_FOREGROUND_COLOR", "black")
SHOW_ENVIRONMENT = config("SHOW_ENVIRONMENT", default=True)

# This setting is used by the csrf_failure view (accounts app).
# You can specify any path that should match the request.path
# Note: the LOGIN_URL Django setting is not used because you could have
# multiple login urls defined.
LOGIN_URLS = [reverse_lazy("admin:login")]


# Default (connection timeout, read timeout) for the requests library (in seconds)
REQUESTS_DEFAULT_TIMEOUT = (10, 30)

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# Django-Admin-Index
#
ADMIN_INDEX_SHOW_REMAINING_APPS = False
ADMIN_INDEX_AUTO_CREATE_APP_GROUP = False
ADMIN_INDEX_SHOW_REMAINING_APPS_TO_SUPERUSERS = True
ADMIN_INDEX_DISPLAY_DROP_DOWN_MENU_CONDITION_FUNCTION = (
    "maykin_common.django_two_factor_auth.should_display_dropdown_menu"
)

#
# DJANGO-AXES
#
# The number of login attempts allowed before a record is created for the
# failed logins. Default: 3
AXES_FAILURE_LIMIT = 10
# If set, defines a period of inactivity after which old failed login attempts
# will be forgotten. Can be set to a python timedelta object or an integer. If
# an integer, will be interpreted as a number of hours. Default: None
AXES_COOLOFF_TIME = 1

#
# MAYKIN-2FA
#
# It uses django-two-factor-auth under the hood so you can configure
# those settings too.
#
# we run the admin site monkeypatch instead.
# Relying Party name for WebAuthn (hardware tokens)
TWO_FACTOR_WEBAUTHN_RP_NAME = f"Open Afval ({ENVIRONMENT})"


#
# DJANGO-HIJACK
#
HIJACK_PERMISSION_CHECK = "maykin_2fa.hijack.superusers_only_and_is_verified"
HIJACK_INSERT_BEFORE = (
    '<div class="content">'  # note that this only applies to the admin
)

# Subpath (optional)
# This environment variable can be configured during deployment.
SUBPATH = (
    f"/{_subpath.strip('/')}" if (_subpath := config("SUBPATH", default="")) else ""
)

#
# DJANGO REST FRAMEWORK
#

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "openafval.api.drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
    ),
    "DEFAULT_PAGINATION_CLASS": "openafval.api.pagination.DynamicPageSizePagination",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "openafval.api.authorization.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("openafval.api.permissions.TokenAuthPermission",),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    #
    # # Filtering
    "ORDERING_PARAM": "ordering",  # 'ordering',
    #
    "PAGE_SIZE": 10,
    # Versioning
    "DEFAULT_VERSION": "1",
    "ALLOWED_VERSIONS": ("1",),
    "VERSION_PARAM": "version",
    #
    # # Exception handling
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

API_VERSION = "0.0.1"

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "TITLE": "Open Afval",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "maykin_common.drf_spectacular.hooks.remove_invalid_url_defaults",
    ],
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
    "TOS": None,
    "VERSION": API_VERSION,
    "TAGS": [],
}
