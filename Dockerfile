ARG VERSION="0935d4e6e251fad97213f11311bc2a2150e3efd9"
FROM mirumee/saleor:${VERSION}

ARG STATIC_URL
ENV STATIC_URL ${STATIC_URL:-/static/}
ENV PYCURL_SSL_LIBRARY=openssl

RUN apt-get update \
    && apt-get install -y \
    git \
    gcc \
    libcurl4 \
    libcurl4-openssl-dev \
    libssl-dev \
    python-psycopg2 \
    python-pycurl \
    python-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


ADD requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

WORKDIR /app

ADD tenants/ ./tenants/
ADD saleor/multitenancy/ saleor/multitenancy/
ADD saleor/settings_multitenant.py saleor/settings_multitenant.py

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
