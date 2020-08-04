ARG VERSION="2.10.2"
FROM mirumee/saleor:${VERSION}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYCURL_SSL_LIBRARY=openssl

RUN apt-get update \
    && apt-get install -y \
    curl \
    gcc \
    git \
    gnupg \
    libcurl4 \
    libcurl4-openssl-dev \
    libssl-dev \
    python-psycopg2 \
    python-pycurl \
    python-dev

ARG PYTHON_XRAY_VERSION="0.0.2"
ARG PYTHON_XRAY_FILE="/tmp/opentracing-python-xray.tar.gz"
ARG PYTHON_XRAY_URL="https://github.com/NyanKiyoshi/opentracing-python-xray/releases/download/${PYTHON_XRAY_VERSION}/opentracing-python-xray.tar.gz"

ARG VERSION
ENV PROJECT_VERSION $VERSION

ADD opentracing-python-xray.gpg .

RUN curl -fLo ${PYTHON_XRAY_FILE} ${PYTHON_XRAY_URL} \
    && curl -fLo ${PYTHON_XRAY_FILE}.sig ${PYTHON_XRAY_URL}.sig \
    && gpg --import opentracing-python-xray.gpg \
    && gpg --verify ${PYTHON_XRAY_FILE}.sig ${PYTHON_XRAY_FILE} \
    && tar -xvf ${PYTHON_XRAY_FILE} \
    && cd opentracing-python-xray-* \
    && ./setup.py install \
    && update-ca-certificates

ADD requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -R /tmp/*

WORKDIR /app

ADD tenants/ ./tenants/
ADD saleor/multitenancy/ saleor/multitenancy/
ADD saleor/settings_multitenant.py saleor/settings_multitenant.py
ADD saleor/wsgi/uwsgi.ini saleor/wsgi/uwsgi.ini

ADD templates/templated_email/dashboard/staff/password.email \
    templates/templated_email/dashboard/staff/password.email

ADD templates/templated_email/compiled/password.html \
    templates/templated_email/compiled/password.html

ADD tests/tenants/ tests/tenants/
ADD tests/settings_multitenant.py tests
ADD tests/api/test_tenants.py tests/api/test_tenants.py
ADD tests/api/pagination/migrations/ tests/api/pagination/migrations/

ADD patches/*.patch patches/
RUN git apply --verbose patches/*.patch

ENV DJANGO_SETTINGS_MODULE="saleor.settings_multitenant"

ARG STATIC_URL
ENV STATIC_URL ${STATIC_URL:-/static/}
RUN SECRET_KEY=dummy STATIC_URL=${STATIC_URL} python3 manage.py collectstatic --no-input
