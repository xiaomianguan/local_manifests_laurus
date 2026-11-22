#!/usr/bin/env bash
# Sync AOSPA Ruby with the laurus local manifests into $LAURUS_ROOT/src.
# LAURUS_ROOT defaults to the directory containing this manifest checkout.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
manifests_dir=$(dirname -- "$tools_dir")
task_root=${LAURUS_ROOT:-$(dirname -- "$manifests_dir")}
repo_tool=${REPO_TOOL:-$task_root/host/bin/repo}
if [[ ! -x "$repo_tool" ]]; then
    mkdir -p "$(dirname -- "$repo_tool")"
    curl -fL --retry 2 https://storage.googleapis.com/git-repo-downloads/repo -o "$repo_tool"
    chmod +x "$repo_tool"
fi
mkdir -p "$task_root/src"
cd "$task_root/src"
if [[ ! -d .repo ]]; then
    "$repo_tool" init -u https://github.com/AOSPA/manifest -b ruby --depth=1 --no-clone-bundle
fi
# An empty repository left by a failed first fetch must not be mistaken for an
# unshallowed checkout, or retries download every branch's history.
repo_patch="$tools_dir/patches/repo-keep-empty-retries-shallow.patch"
if ! git -C .repo/repo apply --reverse --check "$repo_patch" 2>/dev/null; then
    git -C .repo/repo apply "$repo_patch" ||
        printf 'Warning: repo tool patch does not apply to this repo version\n' >&2
fi
# CodeAurora moved to CodeLinaro; Ruby's manifest still names the old host.
sed -i 's#https://source.codeaurora.org/quic/la#https://git.codelinaro.org/clo/la#' .repo/manifests/default.xml
mkdir -p .repo/local_manifests
cp "$manifests_dir"/*.xml .repo/local_manifests/
export GIT_TERMINAL_PROMPT=0
exec "$repo_tool" sync -c --no-manifest-update --no-clone-bundle --no-tags --retry-fetches=1 -j"${SYNC_JOBS:-4}" "$@"
