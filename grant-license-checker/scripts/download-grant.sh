#!/usr/bin/env bash
# Downloads grant binaries from GitHub (https://github.com/anchore/grant/releases/),
# and installs it into `./.grant/`.

set -eu -o pipefail

function log() {
    msg="$1"
    shift
    # shellcheck disable=SC2059 # "$1" for printf is assumed safe.
    printf "$msg\n" "$@" >&2
}

# Add extra logging if the runner was run with debug logging.
test -z "${RUNNER_DEBUG+x}" || set -x

grant_version="${GRANT_VERSION:-0.2.9}"

sha256sums='
d8afd586bd393434ddc76e8c140870ea91df81e3904a875d750d0c4b805ec28a  grant_0.2.9_darwin_amd64.sbom
d8bbc0d65d3e90fcaa416e3231f998701cdd087a06218e02d402df53688675e4  grant_0.2.9_darwin_amd64.tar.gz
fa36151b076a421371d759b4d7c5ae21bc4bf92c5cb17a99453251856aa1cd44  grant_0.2.9_darwin_arm64.sbom
65dca6b8784ef18464c3aa975f69419e98b34d346d7217ac86c66c42b1682dd9  grant_0.2.9_darwin_arm64.tar.gz
26f1acc3db3038dd7e146aef43a7860752f90b9fc93f1ad39f31bff9e0406417  grant_0.2.9_linux_amd64.deb
924241d4736ff1658cd015339f4badee8549b034ed7794c356a9dd77d7a4a661  grant_0.2.9_linux_amd64.rpm
09abdd03a97432796552aa0f7c599be0beff1fbb3e3cbdfe778f785b71d815fd  grant_0.2.9_linux_amd64.sbom
f63c300dfdc8c92a64b5a42263958ba3a03640b7a98fae1bc9dbda7b38d1597b  grant_0.2.9_linux_amd64.tar.gz
9059530a87fd8238e52af8bcd547dc13e506e19d980d89f7ad689af25eb7e09f  grant_0.2.9_linux_arm64.deb
c4e5266e528329e2b0e3c09995fad9332711982ad72b0aa205eded95199da701  grant_0.2.9_linux_arm64.rpm
6e77edf07b5a62250ccc0153c6e73bf647a8f51ebbfd6b72053d9afddfdbf12f  grant_0.2.9_linux_arm64.sbom
b7cb2ea682403ebb558decdc6f1e953ff8cb5ab8732b0d5bd6b072bc4fc72d37  grant_0.2.9_linux_arm64.tar.gz'

kernel=$(uname -s)
arch=$(uname -m)
case "$arch" in
x86_64)
    arch=amd64
    ;;
# Debian returns 'aarch64', Darwin returns 'arm64'.
aarch64 | arm64)
    arch=arm64
    ;;
*)
    log "Unsupported machine architecture: %s"
    exit 1
    ;;
esac

dl_filename="grant_${grant_version}_${kernel,,}_${arch}.tar.gz"
dl_url="https://github.com/anchore/grant/releases/download/v${grant_version}/grant_${grant_version}_${kernel,,}_${arch}.tar.gz"

temp_dl_dir="$(mktemp -d -t grant-download.XXXXXX)"
temp_dl_full_path="${temp_dl_dir}/${dl_filename}"

# Download
log "Downloading grant (%s) to %s...\n" "$dl_url" "$temp_dl_full_path"
curl --fail-early --fail-with-body -Lo "${temp_dl_dir}/${dl_filename}" "$dl_url"

# Checksum
log "Checking Integrity..."
(
    cd "$temp_dl_dir"
    echo "$sha256sums" | sha256sum -c - --ignore-missing || {
        log "Checksum failed"
        exit 1
    }
)

# Install
log "Installing..."
mkdir -p ./.grant
cd ./.grant
tar -xf "$temp_dl_full_path"

# Delete temporary files
log "Deleting downloads..."
rm -v "$temp_dl_full_path"
rmdir -v "$temp_dl_dir"
