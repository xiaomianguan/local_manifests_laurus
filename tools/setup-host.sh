#!/usr/bin/env bash
# Install build dependencies in a rootless userspace, leaving host packages alone.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_root=${LAURUS_ROOT:-$(cd -- "$tools_dir/../.." && pwd)}
mkdir -p "$task_root/host"
cd "$task_root/host"
archive=ubuntu-base-20.04.5-base-amd64.tar.gz
base_url=https://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release
if [[ ! -f "$archive" ]]; then
    curl -fL --retry 2 "$base_url/$archive" -o "$archive"
fi
curl -fL --retry 2 "$base_url/SHA256SUMS" -o SHA256SUMS
python3 - "$archive" <<'PY'
import hashlib
from pathlib import Path
import sys
p = Path(sys.argv[1])
expected = next(line.split()[0] for line in Path('SHA256SUMS').read_text().splitlines() if line.endswith(p.name))
with p.open('rb') as stream:
    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
assert actual == expected, 'Ubuntu base archive checksum mismatch'
PY
if [[ ! -e rootfs/bin/bash ]]; then
    mkdir -p rootfs
    unshare --map-auto --map-root-user --mount --pid --fork tar -xpf "$archive" -C rootfs
fi
"$tools_dir/enter-build-env.sh" bash -ec '
    printf "deb http://archive.ubuntu.com/ubuntu focal main restricted universe multiverse\ndeb http://archive.ubuntu.com/ubuntu focal-updates main restricted universe multiverse\ndeb http://security.ubuntu.com/ubuntu focal-security main restricted universe multiverse\n" > /etc/apt/sources.list
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        git-core gnupg flex bison build-essential zip curl zlib1g-dev \
        gcc-multilib g++-multilib libc6-dev-i386 lib32ncurses5-dev lib32z1-dev \
        libncurses5 libx11-dev libgl1-mesa-dev libxml2-utils xsltproc unzip \
        fontconfig python2 python3 python-is-python3 bc rsync ccache libssl-dev lz4 locales
'
