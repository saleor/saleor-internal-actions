#!/usr/bin/env sh

# USAGE: [TAG] [docker-build-options...]
DOCKER=${DOCKER:-docker}
TAG=${1:-tenant}
shift

set -x
$DOCKER build --build-arg VERSION=master --build-arg UPSTREAM=mirumee/saleor -t "$TAG" "$@" .
