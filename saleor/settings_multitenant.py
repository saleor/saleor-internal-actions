from sys import stderr

from saleor.settings import *  # noqa
from tenants.datadog import DatadogInstaller

PROJECT_VERSION = os.getenv("PROJECT_VERSION")

if not PROJECT_VERSION:
    PROJECT_VERSION = "unknown"
    print("Warning: missing PROJECT_VERSION key", file=stderr)


DD_TRACE_ENABLED: bool = get_bool_from_env("DD_TRACE_ENABLED", False)
if DD_TRACE_ENABLED:
    AGENT_HOST = os.getenv("DD_AGENT_HOST")
    AGENT_PORT = int(os.getenv("DD_TRACE_AGENT_PORT", 8126))

    # Do not set DD_DEBUG to True unless you know what you are doing
    # The behavior changes totally in debug mode and is buggy. It will NOT
    # reflect the same way as in production, results will be totally different.
    #
    # Only prefer and trust DD_LOGGING_LEVEL=DEBUG, it will give more debug information
    # and will not affect how the tracer works.
    DD_DEBUG = get_bool_from_env("DD_TRACE_DEBUG", False)
    DD_LOGGING_LEVEL = os.getenv(
        "DD_LOGGING_LEVEL", "DEBUG" if DD_DEBUG is True else "INFO"
    )

    DatadogInstaller(
        agent_host=AGENT_HOST,
        agent_port=AGENT_PORT,
        project_version=PROJECT_VERSION,
        variables=locals(),
        logging_level=DD_LOGGING_LEVEL,
        debug=DD_DEBUG,
    ).init()


# Multitenancy

ALLOWED_HOSTS = get_list(os.environ.get("ALLOWED_HOSTS", "*"))

TENANT_MODEL = "tenants.Tenant"

# When set to true, it will only send ``SET <schema_name>`` when the schema was actually
# changed rather than before every SQL query.
#
# Value  ---  Number of SQL Queries
# ---------------------------------
# True   ---  N_Queries * 1 + M
#        ---  M => number of schema switches, 99% of the time M = 1
# False  ---  N_Queries * 2
#
TENANT_LIMIT_SET_CALLS = get_bool_from_env("TENANT_LIMIT_SET_QUERIES", True)
ROOT_URLCONF = "tenants.urls"

TENANT_APPS = [*INSTALLED_APPS, "saleor.multitenancy"]
SHARED_APPS = [
    "tenant_schemas",
    "tenants",
    "django.contrib.contenttypes",
]
INSTALLED_APPS = [
    "tenants",
    "tenant_schemas",
    "django_ses",
    *TENANT_APPS,
]

MIDDLEWARE = ("tenants.middleware.SaleorTenantMiddleware", *MIDDLEWARE)

DATABASE_ROUTERS = ("tenant_schemas.routers.TenantSyncRouter",)
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://saleor:saleor@localhost:5432/saleor",
        engine="tenants.postgresql_backend",
        conn_max_age=600,
    )
}

CACHES = {
    "default": dict(
        django_cache_url.config(),
        KEY_FUNCTION="tenant_schemas.cache.make_key",
        REVERSE_KEY_FUNCTION="tenant_schemas.cache.reverse_key",
    )
}

DEFAULT_FILE_STORAGE = "tenants.storages.TenantFileSystemStorage"
if AWS_MEDIA_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = "tenants.storages.TenantS3MediaStorage"


# Celery SQS

CELERY_QUEUE_PREFIX = os.environ.get("CELERY_QUEUE_PREFIX", None)
if CELERY_QUEUE_PREFIX:
    CELERY_BROKER_TRANSPORT_OPTIONS = {"queue_name_prefix": CELERY_QUEUE_PREFIX}

# Other

DEFAULT_BACKUP_BUCKET_NAME = os.environ.get("DEFAULT_BACKUP_BUCKET_NAME")

if os.environ.get("USE_SES", False):
    EMAIL_BACKEND = "django_ses.SESBackend"

CLOUD_SENTRY_DSN = os.getenv("CLOUD_SENTRY_DSN")
if CLOUD_SENTRY_DSN:
    from tenants.sentry import CloudSentry

    CloudSentry(PROJECT_VERSION, CLOUD_SENTRY_DSN).init()
