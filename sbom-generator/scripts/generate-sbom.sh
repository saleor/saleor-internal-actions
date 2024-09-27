#!/usr/bin/env bash

set -eu -o pipefail

function log() {
    msg="$1"
    shift
    # shellcheck disable=SC2059 # "$1" for printf is assumed safe.
    printf "$msg\n" "$@" >&2
}

# Add extra logging if the runner was run with debug logging.
test -z "${RUNNER_DEBUG+x}" || set -x

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
    # Path to the source code to analyze
    "$CONF_PROJECT_DIR"
)

# Add project types into the 'cdxgen' command line argument list.
read -d '' -r -a ecosystems < <(echo "$CONF_ECOSYSTEMS") || true
for ecosystem in "${ecosystems[@]}"; do
    cmd_args+=( "--type=$ecosystem" )
done

# Generate the BOM.
log "Generating SBOM..."
FETCH_LICENSE=true cdxgen "${cmd_args[@]}"
