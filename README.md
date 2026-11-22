# AOSPA Ruby for Xiaomi MI CC 9e (laurus)

Branch `aospa-ruby`: local manifests and build tools for AOSPA Ruby (Android 11).

| Repo | Path |
|---|---|
| [android_device_xiaomi_laurus](https://github.com/xiaomianguan/android_device_xiaomi_laurus) | `device/xiaomi/laurus` |
| [proprietary_vendor_xiaomi_laurus](https://github.com/xiaomianguan/proprietary_vendor_xiaomi_laurus) | `vendor/xiaomi/laurus` |
| [aospa_kernel_xiaomi_laurus](https://github.com/xiaomianguan/aospa_kernel_xiaomi_laurus) | `kernel/xiaomi/laurus` |
| [aospa_frameworks_base](https://github.com/xiaomianguan/aospa_frameworks_base) | `frameworks/base` |
| [aospa_frameworks_native](https://github.com/xiaomianguan/aospa_frameworks_native) | `frameworks/native` |

## Build from scratch

```bash
mkdir aospa-laurus && cd aospa-laurus
git clone -b aospa-ruby https://github.com/xiaomianguan/local_manifests_laurus
local_manifests_laurus/tools/setup-host.sh   # rootless Ubuntu 20.04 build userspace in host/
local_manifests_laurus/tools/sync.sh         # repo init + sync into src/
# Optional: mkdir -p local-apps && cp /path/to/AnotherWidget.apk local-apps/LaurusAnotherWidget.apk
local_manifests_laurus/tools/build.sh vanilla
local_manifests_laurus/tools/build.sh gapps
```

Results land in `artifacts/vanilla/` and `artifacts/gapps/`: the flashable
non-A/B OTA ZIP, boot/recovery/dtbo/vbmeta images, the exact source lock, and
SHA-256 sums. The workspace directory is the parent of this checkout; set
`LAURUS_ROOT` to use another one.

* `setup-host.sh` needs no root and changes no host packages; builds run in
  `host/rootfs` through `enter-build-env.sh`. On an existing Ubuntu 20.04-style
  build host you can instead sync normally (below) and use `lunch`/`m bacon`.
* `sync.sh` downloads the `repo` launcher to `host/bin/repo` if needed (or set
  `REPO_TOOL`), points the old CodeAurora URLs at CodeLinaro, patches the repo
  tool so retried shallow fetches stay shallow, and copies these manifests to
  `src/.repo/local_manifests`.
* `build.sh` fetches the prebuilt apps (`device/xiaomi/laurus/apps/fetch-apps.py`),
  the GMS LFS binaries for GApps (`fetch-gms-lfs.py`, no host git-lfs needed),
  builds with `BUILD_JOBS` (default 6, sized for 16 GiB RAM), then verifies
  the Google APK signatures (`check-gapps-signatures.py`) and the package
  (`check-artifacts.py`) before exporting.
* Another Widget can't be downloaded automatically. Without
  `local-apps/LaurusAnotherWidget.apk` the build leaves it out;
  `LAURUS_SKIP_ANOTHER_WIDGET=1` does so even when present.
* With systemd-oomd, run the build in its own unit so memory pressure can't
  take down your desktop session:
  `systemd-run --user --unit=laurus-build -p MemoryHigh=11G local_manifests_laurus/tools/build.sh gapps`

## Manual sync

```bash
git config --global url."https://git.codelinaro.org/clo/la".insteadOf https://source.codeaurora.org/quic/la
repo init -u https://github.com/AOSPA/manifest -b ruby --depth=1 --no-clone-bundle
git clone -b aospa-ruby https://github.com/xiaomianguan/local_manifests_laurus .repo/local_manifests
repo sync -c --no-clone-bundle --no-tags
device/xiaomi/laurus/apps/fetch-apps.py
```

## Manifests

* `laurus.xml`: the repos above, Nicobar HAL branches for trinket, the
  relocated GMS, Wayland and Trade Federation repos, and no bootloader build.
* `zz-caf-revisions.xml`: pins Qualcomm projects to the exact SHAs of the
  original Ruby releases (LA.QSSI.11.0.r1-12300-qssi.0 and
  LA.UM.9.14.r1-16900-LAHAINA.0), whose tags did not survive the move to
  CodeLinaro. Regenerate with `tools/pin-caf-revisions.py` from
  `repo manifest` output; the release manifests are in `tools/caf-releases`.

Porting notes and hardware test status: [tools/PORTING-NOTES.md](tools/PORTING-NOTES.md).
Do not flash Mi A3 firmware, bootloaders, partition tables or A/B conversion packages.
