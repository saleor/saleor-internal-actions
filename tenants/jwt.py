from typing import Optional

import jwt
from django.core.handlers.wsgi import WSGIRequest
from django.db import connection
from graphql_jwt.settings import jwt_settings

from saleor.graphql.utils import create_jwt_payload


def get_tenant(context: Optional[WSGIRequest] = None):
    if context is not None:
        return context.tenant
    else:
        return connection.tenant


def jwt_issuer(context: Optional[WSGIRequest] = None):
    return get_tenant(context).domain_url


def jwt_secret(context=None):
    key = get_tenant(context).jwt_secret_key
    return key


def jwt_payload(user, context=None):
    payload = create_jwt_payload(user, context)
    payload["iss"] = jwt_issuer(context=context)
    return payload


def jwt_encode(payload, context=None):
    return jwt.encode(payload, jwt_secret(context), jwt_settings.JWT_ALGORITHM).decode(
        "utf-8"
    )


def jwt_decode(token, context=None):
    return jwt.decode(
        token,
        jwt_secret(context),
        jwt_settings.JWT_VERIFY,
        options={"verify_exp": jwt_settings.JWT_VERIFY_EXPIRATION},
        leeway=jwt_settings.JWT_LEEWAY,
        audience=jwt_settings.JWT_AUDIENCE,
        algorithms=[jwt_settings.JWT_ALGORITHM],
        issuer=jwt_issuer(context=context),
    )
