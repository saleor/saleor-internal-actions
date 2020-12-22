from django.conf.urls import url

from saleor.urls import urlpatterns as baseurls

from tenants.asgi.health import health_check

urlpatterns = [
    url(r"live/", health_check, name="healthcheck"),
    *baseurls,
]