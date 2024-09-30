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

grant_version="${GRANT_VERSION:-0.2.1}"

sha256sums='
7c5d161b2c32db49a5518fd25ea2f07f15e0a11423e479a1b3f6eb5707137a53  grant_0.2.1_darwin_amd64.sbom
e9da0ecadf819e0c11489b244fc92a9a1c918cb795c2dd605682881fd806821a  grant_0.2.1_darwin_amd64.tar.gz
d636bb55c3ab7e6043209f9288cdb3f572ac597e49bb53422602b4b2ac670e28  grant_0.2.1_darwin_arm64.sbom
bc5861697b97a4f23dfee496fb54db667de3b863311dee18bff836e9200d8608  grant_0.2.1_darwin_arm64.tar.gz
299bcb89f3b0d8ff86c8713fee30fcb4449e021256a38802d8c1f7e06c7fd81c  grant_0.2.1_linux_amd64.deb
9bef595e4b65bf9fd6c6c11af72c68f70f9a24c4c19b79a58fd99bb5f477456e  grant_0.2.1_linux_amd64.rpm
f0404f192045074f9089a6be621a27c8eee50c3143a7a45f454485c756c1bbff  grant_0.2.1_linux_amd64.sbom
2b1620ac640c9db8d376847b12835fba9ae75d85c9a36981305ff12859b55280  grant_0.2.1_linux_amd64.tar.gz
9cd94d462c1607ef7f5b2a17f9451dd2ea358e995b44ca3ba35312edf725ade6  grant_0.2.1_linux_arm64.deb
043184053aaab7e49fffe2ac2a5056c712e9ba8c45769f93bfa8bd2633176373  grant_0.2.1_linux_arm64.rpm
d0aa2733b753eb671dd86529b11464a99a12cf2659864203a2a6cad21d2b1231  grant_0.2.1_linux_arm64.sbom
c51b871fece7a00c896c6b6c94f824a72cebee503f3f1a87ebd4803508a765a1  grant_0.2.1_linux_arm64.tar.gz'

kernel=$(uname -s)
arch=$(uname -m)
case "$arch" in
    x86_64)
        arch=amd64 ;;
    # Debian returns 'aarch64', Darwin returns 'arm64'.
    aarch64|arm64)
        arch=arm64 ;;
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
