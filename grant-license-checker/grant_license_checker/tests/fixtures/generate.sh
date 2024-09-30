#!/usr/local/bin/bash
# Script generating the fixtures: sample-sbom-vXX.json and sample-grant-report.json
set -eu -o pipefail

function log() {
    msg="$1"
    shift
    # shellcheck disable=SC2059 # "$1" for printf is assumed safe.
    printf "$msg\n" "$@" >&2
}

sample_project_dir=./sample-project
cyclonedx_spec_version='1.5'

# If the sample project exists, delete it.
if [ -d "$sample_project_dir" ]; then
    rm -vR "$sample_project_dir"
fi

# Create the sample project.
mkdir "$sample_project_dir"
cd "$sample_project_dir"

log "Generating sample project..."
tee pyproject.toml >/dev/null <<'EOF'
[tool.poetry]
name = "example-project"
version = "0.1.0"
description = "An example SBOM project"
authors = ["Saleor Commerce <hello@saleor.io>"]
license = "BSD-3-Clause"
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.12"
django = "*"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

tee .grant.yaml >/dev/null <<'EOF'
rules:
  - pattern: "*"
    name: "default-allow-all"
    mode: "allow"
EOF

log "Generating Poetry.lock..."
poetry lock --quiet

log "Generating SBOM..."
docker run --rm \
   -v "$PWD":/app:rw \
   --env FETCH_LICENSE=true \
   -t ghcr.io/cyclonedx/cdxgen:v10.9.5 \
   --recurse \
   -o /app/bom.json \
   --profile license-compliance \
   --spec-version "$cyclonedx_spec_version" \
   /app

# Make the SBOM human readable, and copy it into the fixtures.
log "Adapting and copying SBOM..."
jq . ./bom.json > ../sample-sbom-v"$cyclonedx_spec_version".json

log "Generating grant JSON file..."
grant check \
    -o json \
    --non-spdx \
    ../sample-sbom-v"$cyclonedx_spec_version".json | jq . > ../sample-grant-report.json
