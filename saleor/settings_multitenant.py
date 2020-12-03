from sys import stderr

import opentracing as ot

from saleor.settings import *  # noqa


PROJECT_VERSION = os.getenv("PROJECT_VERSION")

if not PROJECT_VERSION:
    PROJECT_VERSION = "unknown"
    print("Warning: missing PROJECT_VERSION key", file=stderr)


# Datadog APM agent for distributed tracing
# Note we cannot import anything from ddtrace otherwise it will be initialized
# It needs to be called as soon as possible due to monkey-patching starting
# as soon as imported.

DD_TRACE_ENABLED: bool = get_bool_from_env("DD_TRACE_ENABLED", False)
# Configuration keys for the global tracer (a base datadog tracer that is used inside
# the Datadag opentracing tracer):
#   https://docs.datadoghq.com/tracing/setup_overview/setup/python#configuration
#
# For Django support configuration:
#   https://ddtrace.readthedocs.io/en/stable/integrations.html#django
if DD_TRACE_ENABLED:
    # Set project version before importing DataDog tracer
    # as it will try to find this key during import
    os.environ["DD_VERSION"] = PROJECT_VERSION

    import ddtrace.opentracer as dd_ot
    from ddtrace.opentracer.settings import ConfigKeys as ddKeys

    def init_datadog_tracer(service_name: str, config):
        # For configuration details, refer to
        # https://ddtrace.readthedocs.io/en/stable/advanced_usage.html#opentracing
        # Note `settings` key is for setting up filters
        tracer = dd_ot.Tracer(service_name, config=config)
        dd_ot.set_global_tracer(tracer)
        return tracer

    init_datadog_tracer(
        os.environ.get("DD_SERVICE"),
        {
            ddKeys.AGENT_HOSTNAME: os.environ.get("DD_AGENT_HOST"),
            ddKeys.AGENT_PORT: int(os.environ.get("DD_TRACE_AGENT_PORT", 8126)),
            ddKeys.DEBUG: get_bool_from_env("DD_TRACE_DEBUG", False),
            ddKeys.ENABLED: DD_TRACE_ENABLED,
        },
    )

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
    "django_prometheus",
    *TENANT_APPS,
]

MIDDLEWARE = (
    [
        "django_prometheus.middleware.PrometheusBeforeMiddleware",
        "tenants.middleware.SaleorTenantMiddleware",
    ]
    + MIDDLEWARE
    + ["django_prometheus.middleware.PrometheusAfterMiddleware"]
)

ROOT_URLCONF = "saleor.urls_prometheus_wrapper"
PROMETHEUS_EXPORT_MIGRATIONS = False

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
