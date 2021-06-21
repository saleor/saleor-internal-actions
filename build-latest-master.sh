#!/usr/bin/env sh

# USAGE: [TAG] [docker-build-options...]
DOCKER=${DOCKER:-docker}
TAG=${1:-tenant}
shift

UPSTREAM=mirumee/saleor
VERSION=master

set -x
$DOCKER pull "$UPSTREAM":"$VERSION"
$DOCKER build --build-arg VERSION="$VERSION" --build-arg UPSTREAM="$UPSTREAM" -t "$TAG" "$@" .
