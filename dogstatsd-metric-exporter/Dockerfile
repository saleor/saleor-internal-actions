# Stages:
# - build:
#     Installation of Python and requirements,
#     then builds a wheel at: /tmp/dogstatsd_metric_exporter-<version>-py3-none-any.whl
# - DogStatsDExporter: base and minimal Python image with DogStatsDExporter installed
# - example: an example Flask application with metrics taken from ./example
#
FROM python:3.9-alpine3.13 AS build

WORKDIR /build

COPY MANIFEST.in ./
COPY setup.* ./
COPY dogstatsd_metric_exporter/ ./dogstatsd_metric_exporter/

RUN set -ex; \
  pip install '.[build]'; \
  ./setup.py bdist_wheel

# EXPORTER
FROM python:3.9-alpine3.13 as DogStatsDExporter
ARG VERSION="0.0.0"

COPY --from=build /build/dist/dogstatsd_metric_exporter-"$VERSION"-py3-none-any.whl /tmp

RUN pip install /tmp/dogstatsd_metric_exporter-"$VERSION"-py3-none-any.whl

# EXAMPLE APP
FROM DogStatsDExporter as example
WORKDIR /app

COPY example ./example/
RUN pip install -r ./example/requirements.txt

ARG APP_PORT=5542
ARG APP_HOST="0.0.0.0"

ENV APP_PORT="${APP_PORT}" APP_HOST="${APP_HOST}"

ENV PYTHONPATH="/app"
EXPOSE "${APP_PORT}"
ENTRYPOINT [ "python" ]
CMD [ "example/app.py" ]
