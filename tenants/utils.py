from typing import Any, Type

from django.core.exceptions import ValidationError
from django.db import models
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
