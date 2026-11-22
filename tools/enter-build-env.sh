#!/usr/bin/env bash
# Run a command in an isolated Ubuntu 20.04 userspace, without root privileges.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_root=${LAURUS_ROOT:-$(cd -- "$tools_dir/../.." && pwd)}
export LAURUS_BUILD_ROOT="$task_root"
exec unshare --map-auto --map-root-user --mount --pid --fork bash -euc '
    rootfs="$LAURUS_BUILD_ROOT/host/rootfs"
    mount --make-rprivate /
    mount --rbind /dev "$rootfs/dev"
    mount -t proc proc "$rootfs/proc"
    if [[ ! -e "$rootfs/etc/mtab" && ! -L "$rootfs/etc/mtab" ]]; then
        ln -s /proc/self/mounts "$rootfs/etc/mtab"
    fi
    mount --rbind /sys "$rootfs/sys"
    mkdir -p "$rootfs/workspace" "$rootfs/tmp"
    mount --bind "$LAURUS_BUILD_ROOT" "$rootfs/workspace"
    mount -t tmpfs -o size=2G tmpfs "$rootfs/tmp"
    cp -L /etc/resolv.conf "$rootfs/etc/resolv.conf"
    exec chroot "$rootfs" /usr/bin/env -i \
        HOME=/root USER=root LANG=C.UTF-8 LC_ALL=C.UTF-8 \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        /bin/bash -c '\''cd /workspace/src; exec "$@"'\'' bash "$@"
' bash "$@"
