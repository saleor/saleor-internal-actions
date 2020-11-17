from functools import wraps
from typing import Any, Type, List
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models, connection
from django.db.models import Field
from django.http.request import validate_host as django_validate_host


def clean_fields(model: Type[models.Model], **field_values: Any) -> None:
    errors = {}

    for field_name, field_value in field_values.items():
        field: Field = model._meta.get_field(field_name)
        try:
            field.clean(value=field_value, model_instance=None)
        except ValidationError as exc:
            errors = exc.update_error_dict(errors)

    if errors:
        raise ValidationError(errors)


def preserve_tenant(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        tenant = connection.tenant
        val = f(*args, **kwargs)
        connection.set_tenant(tenant)
        return val

    return wrapper


def assure_connection_initialized(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if connection.connection is None:
            # That's a hax, without fetch query we have no access to
            # database connection details required later for connecting psql
            from tenants.models import Tenant

            Tenant.objects.get()
        return f(*args, **kwargs)

    return wrapper


def validate_client_host(host):
    domain = get_tenant_domain(host)
    if domain == connection.tenant.domain_url:
        return True
    else:
        allowed_hosts = origins_to_hosts(connection.tenant.allowed_client_origins)
        return django_validate_host(host, allowed_hosts)


def get_tenant_domain(host):
    if not host.endswith(".saleor.cloud"):
        return host

    domain_parts = host.split(".")
    label_parts = domain_parts[0].split("-")
    if len(label_parts) > 1:
        domain_parts[0] = label_parts[-1]
    return ".".join(domain_parts)


def origins_to_hosts(origins: List[str]) -> List[str]:
    if origins == ["*"]:
        return origins
    return [urlparse(origin).hostname for origin in origins]
