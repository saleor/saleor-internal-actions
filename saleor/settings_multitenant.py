import os
import dj_database_url
import django_cache_url
import opentracing
import xray_ot

from saleor.settings import *  # noqa

# Multitenancy

ALLOWED_HOSTS = get_list(os.environ.get("ALLOWED_HOSTS", "*"))

TENANT_MODEL = "tenants.Tenant"

TENANT_APPS = [*INSTALLED_APPS, "saleor.multitenancy"]
SHARED_APPS = [
    "tenant_schemas",
    "tenants",
    "django.contrib.contenttypes",
    "django_version",
]
INSTALLED_APPS = [
    "tenants",
    "tenant_schemas",
    "django_ses",
    "django_version",
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

# X-Ray
PROJECT_VERSION = os.environ.get("PROJECT_VERSION", "undefined")
XRAY_COLLECTOR_HOST = os.environ.get("COLLECTOR_HOST", None)
XRAY_COLLECTOR_PORT = int(os.environ.get("COLLECTOR_PORT", 2000))
XRAY_COLLECTOR_VERBOSITY = int(os.environ.get("COLLECTOR_VERBOSITY", 1))

if XRAY_COLLECTOR_HOST:
    tracer = xray_ot.Tracer(
        component_name="Saleor-Staging",
        collector_host=XRAY_COLLECTOR_HOST,
        collector_port=XRAY_COLLECTOR_PORT,
        verbosity=XRAY_COLLECTOR_VERBOSITY,
    )
    opentracing.set_global_tracer(tracer)
