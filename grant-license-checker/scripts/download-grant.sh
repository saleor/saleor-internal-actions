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

grant_version="${GRANT_VERSION:-0.2.2}"

sha256sums='
cb5925f6a1d7a791261914f27ea300ab3e88fa18521c5fff1b88d573fa349092  grant_0.2.2_darwin_amd64.sbom
9d65808b30107f46d4755e8840b756a2abbbc60110485cf44df1d5f76a1fe418  grant_0.2.2_darwin_amd64.tar.gz
14d2e8fbe14f6699201822f1744056e6fce8dc6787eeeacebbd6c37b11c27bdb  grant_0.2.2_darwin_arm64.sbom
a169e2bf5dd755b35d3a0d05f9228ef1c32706611a18c86730f162399536ad8d  grant_0.2.2_darwin_arm64.tar.gz
5c2a2db8aeca438cda9fee3c1bd93c07f8cd923aae53c35b385f710525fbd083  grant_0.2.2_linux_amd64.deb
e37fb1d23c23d567fd026fb245bd49e14ec57c3ed2fa62c51a167c1a96b34d33  grant_0.2.2_linux_amd64.rpm
17f18dad481ca1f15c1baa7c2ad3d322b9a467b26af4d4c6fa3aef33a4b146d7  grant_0.2.2_linux_amd64.sbom
5c61efc0cad3def981642386a8ad813fdc74ef5c6e42ded38ffe2c4df1bd9060  grant_0.2.2_linux_amd64.tar.gz
2a39884630cf8d928947e21aca0a44b6ad0504337b349dc42d5378661875ec54  grant_0.2.2_linux_arm64.deb
048bab95a2284fa2a8a124afe27ba64821641bf48c1cdf498068a86208feae74  grant_0.2.2_linux_arm64.rpm
3e59bc00a54c6d99bec529e0fcc710d0b75edb8211ead0ff995b935be3fa433a  grant_0.2.2_linux_arm64.sbom
2510d17bdc5a52e3a6332fd158c6a7b888f12f5e9f31b31d2222765b97330971  grant_0.2.2_linux_arm64.tar.gz'

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
