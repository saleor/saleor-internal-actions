ARG VERSION="3.0.0-a.28"
ARG UPSTREAM="ghcr.io/mirumee/saleor"
FROM ${UPSTREAM}:${VERSION} as prod

ENV DEBIAN_FRONTEND=noninteractive
ENV PYCURL_SSL_LIBRARY=openssl

RUN apt-get update \
    && apt-get install -y \
    gcc \
    git \
    libcurl4 \
    libcurl4-openssl-dev \
    libssl-dev \
    python-psycopg2 \
    python-pycurl \
    python-dev \
    postgresql-client-11

ADD dogstatsd-metric-exporter/ dogstatsd-metric-exporter/
ADD requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -R /tmp/*

WORKDIR /app

ADD tenants/ ./tenants/
ADD saleor/multitenancy/ saleor/multitenancy/
ADD saleor/settings_multitenant.py saleor/settings_multitenant.py
ADD saleor/gunicorn_config.py saleor/gunicorn_config.py
ADD saleor/wsgi/uwsgi.ini saleor/wsgi/uwsgi.ini
ADD saleor/tests/migrations/ saleor/tests/migrations/
ADD saleor/graphql/tests/test_tenants.py saleor/graphql/tests/test_tenants.py

ADD patches/*.patch patches/
RUN git apply --verbose patches/*.patch

ENV DJANGO_SETTINGS_MODULE="saleor.settings_multitenant"

ARG STATIC_URL
ENV STATIC_URL ${STATIC_URL:-/static/}
RUN OPTL_NAMESPACE=build SECRET_KEY=dummy STATIC_URL=${STATIC_URL} python3 manage.py collectstatic --no-input

ENV PORT 8000
ENV PROCESSES 4

ARG IMAGE_VERSION
ENV PROJECT_VERSION=${IMAGE_VERSION}

RUN test -n "$PROJECT_VERSION" || echo "Warning: IMAGE_VERSION Argument was not passed" >&2

CMD ["uwsgi", "--ini", "/app/saleor/wsgi/uwsgi.ini"]

### Extend the default multitenant prod image with plugins
FROM prod as plugins

ADD extra-plugins/ extra-plugins/
RUN for f in $(find extra-plugins -maxdepth 1 -mindepth 1 -type d); do \
    ( \
    set -ex; \
    cd $f; \
    python setup.py install \
    ); \
    done
