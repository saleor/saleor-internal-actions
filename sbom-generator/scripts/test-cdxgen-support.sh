#!/usr/bin/env bash

set -eu -o pipefail

SELF_FILENAME=$(basename "$0")
HERE=$(dirname "$(readlink -f "$0")")

cd "$HERE"

# Options (populated via parse_opts())
cdxgen_version=

usage() {
  {
    echo "USAGE: $SELF_FILENAME <OPTIONS...>"
    echo ""
    echo "OPTIONS"
    echo "   --cdxgen-version  The version of cdxgen to use (https://github.com/CycloneDX/cdxgen/releases)"
    echo "                     Example value: v11.6.0"
  } >&2
}

info() {
  echo "INFO: $*" >&2
}

error() {
  echo "ERROR: $*" >&2
}

tempdir=$(mktemp -d)

cleanup() {
  # NOTE: -f is needed to delete .git/ folders
  # rm -Rf "$tempdir"
  :
}

trap cleanup EXIT

# Checks whether a value was provided (in $2).
#
# peek_next_opt_or_fail(args...)
peek_next_opt_or_fail() {
  if [[ "${2-}" == "" ]]; then
    error "Invalid usage: missing argument for $1"
    usage
    exit 1
  fi
}

parse_opts() {
  local incr_count=0
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
    --cdxgen-version)
      peek_next_opt_or_fail "$@"
      cdxgen_version="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      error "Invalid usage: unknown option: $1"
      usage
      exit 1
      ;;
    esac

    incr_count=$((incr_count + 1))
    if [[ "$incr_count" -gt 100 ]]; then
      error "FATAL: infinite loop detected in parse_opts()"
      exit 1
    fi
  done

  if [[ -z "$cdxgen_version" ]]; then
    error "Missing required option: --cdxgen-version"
    usage
    exit 1
  fi
}

# Generates a SBOM for a given project. SBOM will be inside the root directory
# of the project under bom.json ($project_path/bom.json)
#
# run_cdxgen(project_path)
run_cdxgen() {
  local project_path="$1"
  CONF_PROJECT_DIR="$project_path" \
    CONF_ECOSYSTEMS='javascript python' \
    CONF_RESULT_PATH="$project_path"/bom.json ./generate-sbom.sh
}

test_saleor_core() {
  local project_path="$tempdir/core"
  local bom_path="$project_path/bom.json"

  info "Cloning Saleor Core into $project_path..."
  git clone --quiet --depth=1 https://github.com/saleor/saleor "$project_path"

  info "Generating SBOM..."
  run_cdxgen "$project_path"

  # Ensures Python support works by checking whether a BSD-3-Clause license
  # was found for Django (PyPI using `uv` package manager)
  info "Checking Django license..."
  if ! jq -r --exit-status \
    '.components[] | select (.name == "Django") | .licenses[].license | select(.id == "BSD-3-Clause") | {id}' \
    "$bom_path"; then
    error "Test failed: didn't find Django with a BSD-3-Clause license for Saleor Core's SBOM"
    exit 1
  fi

  # Ensures NPM support works
  info "Checking 'release-it' license..."
  if ! jq -r --exit-status \
    '.components[] | select (.name == "release-it") | .licenses[].license | select(.id == "MIT") | {id}' \
    "$bom_path"; then
    error "Test failed: didn't find 'release-it' (NPM) with a MIT license for Saleor Core's SBOM"
    exit 1
  fi
}

test_saleor_apps() {
  local project_path="$tempdir/apps"
  local bom_path="$project_path/bom.json"

  info "Cloning Apps into $project_path..."
  git clone --quiet --depth=1 https://github.com/saleor/apps "$project_path"

  info "Generating SBOM..."
  run_cdxgen "$project_path"

  # Checks for PNPM support (using 'stripe' from NPM)
  info "Checking Stripe license..."
  if ! jq -r --exit-status \
    '.components[] | select (.name == "stripe") | .licenses[].license | select(.id == "MIT") | {id}' \
    "$bom_path"; then
    error "Test failed: didn't find Stripe with a MIT license for Saleor-Apps's SBOM"
    exit 1
  fi
}

main() {
  parse_opts "$@"

  npm install -g "@cyclonedx/cdxgen@$cdxgen_version"

  # Tests a project that uses both NPM & 'uv' (Python)
  test_saleor_core

  # Tests a mono-repo project which has thousands of dependencies
  # (ensures mono-repo works, and doesn't lead to OOM kills)
  test_saleor_apps
}

main "$@"
