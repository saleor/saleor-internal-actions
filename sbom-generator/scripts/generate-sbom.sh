#!/usr/bin/env bash

set -eu -o pipefail

function log() {
    msg="$1"
    shift
    # shellcheck disable=SC2059 # "$1" for printf is assumed safe.
    printf "$msg\n" "$@" >&2
}

# Add extra logging if the runner was run with debug logging.
if [[ -n "${RUNNER_DEBUG+x}" ]]; then
    set -x

    # Enable debug mode for cdxgen
    # (docs: https://cyclonedx.github.io/cdxgen/#/ENV)
    export CDXGEN_DEBUG_MODE=debug
fi

# User provided preferences:
# - CONF_PROJECT_DIR: the path of the project to scan (relative or absolute).
# - CONF_ECOSYSTEMS: list of ecosystems to scan (e.g., python), whitespace separated.
# - CONF_RESULT_PATH: the path where to store the SBOM.
CONF_PROJECT_DIR="${CONF_PROJECT_DIR:-$PWD}"
CONF_ECOSYSTEMS="${CONF_ECOSYSTEMS:-}"
CONF_RESULT_PATH=${CONF_RESULT_PATH:-./bom.json}

cmd_args=(
    "--recurse"
    "--output=$CONF_RESULT_PATH"
    "--profile=license-compliance"
    "--spec-version=1.5" # grant-summarize only supports 1.5 currently
    # Path to the source code to analyze
    "$CONF_PROJECT_DIR"
)

# Add project types into the 'cdxgen' command line argument list.
read -d '' -r -a ecosystems < <(echo "$CONF_ECOSYSTEMS") || true
for ecosystem in "${ecosystems[@]}"; do
    cmd_args+=("--type=$ecosystem")
done

# Generate the BOM.
log "Generating SBOM..."
FETCH_LICENSE=true cdxgen "${cmd_args[@]}"
