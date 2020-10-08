from django.conf.urls import include, url

urlpatterns = []

urlpatterns.append(url("prometheus/", include("django_prometheus.urls")))
urlpatterns.append(url("", include("saleor.urls")))
