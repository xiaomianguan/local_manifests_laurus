#!/usr/bin/env bash
# Build pa_laurus in the Ubuntu 20.04 userspace and export it to $LAURUS_ROOT/artifacts/<variant>.
#   tools/build.sh [vanilla|gapps]
# Another Widget is optional: put its APK at $LAURUS_ROOT/local-apps/LaurusAnotherWidget.apk
# (or set LAURUS_ANOTHER_WIDGET_APK); LAURUS_SKIP_ANOTHER_WIDGET=1 leaves it out.
set -euo pipefail
tools_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
task_root=${LAURUS_ROOT:-$(cd -- "$tools_dir/../.." && pwd)}
export LAURUS_ROOT=$task_root
variant=${1:-vanilla}
case "$variant" in
    vanilla) disables_gms=true ;;
    gapps) disables_gms=false ;;
    *) printf 'Usage: %s [vanilla|gapps]\n' "$0" >&2; exit 2 ;;
esac
device="$task_root/src/device/xiaomi/laurus"
[[ -d "$device" ]] || { printf 'Run %s/sync.sh first\n' "$tools_dir" >&2; exit 1; }
[[ -e "$task_root/host/rootfs/bin/bash" ]] || { printf 'Run %s/setup-host.sh first\n' "$tools_dir" >&2; exit 1; }

mkdir -p "$device/apps/prebuilt"
widget=${LAURUS_ANOTHER_WIDGET_APK:-$task_root/local-apps/LaurusAnotherWidget.apk}
if [[ -z "${LAURUS_SKIP_ANOTHER_WIDGET:-}" && -f "$widget" ]]; then
    cp "$widget" "$device/apps/prebuilt/LaurusAnotherWidget.apk"
else
    rm -f "$device/apps/prebuilt/LaurusAnotherWidget.apk"
fi
python3 "$device/apps/fetch-apps.py"
if [[ "$disables_gms" == false ]]; then
    python3 "$tools_dir/fetch-gms-lfs.py"
fi
# Qualcomm's outer Ninja rule omits kernel source dependencies. Drop only its
# generated Image.gz so Kbuild gets a chance to process source/DTS edits.
rm -f "$task_root/src/out/target/product/laurus/obj/kernel/msm-4.14/arch/arm64/boot/Image.gz"
"$tools_dir/enter-build-env.sh" bash -c '
    set -e
    export TARGET_DISABLES_GMS="${2}"
    source build/envsetup.sh
    lunch pa_laurus-userdebug
    m -j"${1}" kernel
    m -j"${1}" bacon
' bash "${BUILD_JOBS:-6}" "$disables_gms"

out="$task_root/src/out/target/product/laurus"
ota=$(ls -t "$out"/pa-ruby-*-laurus-*.zip | head -1)
check_args=(--ota "$ota")
if [[ "$disables_gms" == false ]]; then
    python3 "$tools_dir/check-gapps-signatures.py"
    check_args+=(--gapps)
fi
python3 "$tools_dir/check-artifacts.py" "${check_args[@]}" "$out"

export_dir="$task_root/artifacts/$variant"
rm -rf "$export_dir.new"
mkdir -p "$export_dir.new"
name=$(basename "$ota" .zip)
cp --reflink=auto "$ota" "$export_dir.new/$name-$variant.zip"
for image in boot.img recovery.img dtbo.img vbmeta.img; do
    cp --reflink=auto "$out/$image" "$export_dir.new/"
done
(cd "$task_root/src" && "${REPO_TOOL:-$task_root/host/bin/repo}" manifest -r -o "$export_dir.new/source-lock.xml" >/dev/null 2>&1) || true
(cd "$export_dir.new" && sha256sum -- * > SHA256SUMS)
rm -rf "$export_dir.old"
[[ -d "$export_dir" ]] && mv "$export_dir" "$export_dir.old"
mv "$export_dir.new" "$export_dir"
rm -rf "$export_dir.old"
printf 'Exported %s\n' "$export_dir/$name-$variant.zip"
