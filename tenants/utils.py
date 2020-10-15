from functools import wraps
from typing import Any, Type

from django.core.exceptions import ValidationError
from django.db import models, connection
from django.db.models import Field


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
