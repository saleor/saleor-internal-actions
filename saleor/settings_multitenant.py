import os
import dj_database_url
import django_cache_url

from saleor.settings import *  # noqa

# Multitenancy

ALLOWED_HOSTS = get_list(os.environ.get("ALLOWED_HOSTS", "*"))

TENANT_MODEL = "tenants.Tenant"

TENANT_APPS = [*INSTALLED_APPS, "saleor.multitenancy"]
SHARED_APPS = ["tenant_schemas", "tenants", "django.contrib.contenttypes"]
INSTALLED_APPS = ["tenants", "tenant_schemas", "django_ses", *TENANT_APPS]

MIDDLEWARE = ["tenants.middleware.SaleorTenantMiddleware"] + MIDDLEWARE

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


GRAPHQL_JWT = {
    **GRAPHQL_JWT,
    "JWT_ENCODE_HANDLER": "tenants.jwt.jwt_encode",
    "JWT_DECODE_HANDLER": "tenants.jwt.jwt_decode",
    "JWT_PAYLOAD_HANDLER": "tenants.jwt.jwt_payload",
}

# Celery SQS

CELERY_QUEUE_PREFIX = os.environ.get("CELERY_QUEUE_PREFIX", None)
if CELERY_QUEUE_PREFIX:
    CELERY_BROKER_TRANSPORT_OPTIONS = {"queue_name_prefix": CELERY_QUEUE_PREFIX}

# Other

DEFAULT_BACKUP_BUCKET_NAME = os.environ.get("DEFAULT_BACKUP_BUCKET_NAME")

if os.environ.get("USE_SES", False):
    EMAIL_BACKEND = "django_ses.SESBackend"
