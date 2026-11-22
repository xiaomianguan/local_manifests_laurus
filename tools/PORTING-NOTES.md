# Porting notes: AOSPA Ruby for Xiaomi MI CC 9e (laurus)

The Android 11 Ruby userdebug build completed successfully on 2026-11-17.
The package is experimental. Recovery and Android boot on the CC9e, ADB works,
and Android reports `sys.boot_completed=1`. The modem reports its baseband
version after the RMTFS memory-permission fix. Full hardware testing is pending.

The initial device tree is derived from AOSPA's Ruby Mi A3 tree at
`f27854f36cc51882a49bda7fa6a0f4bf030a3b0b`:
https://github.com/AOSPA/android_device_xiaomi_laurel_sprout/tree/ruby

## Confirmed stock differences

The device product explicitly uses the fingerprint extracted from stock system
and vendor properties:
`Xiaomi/laurus/laurus:10/QKQ1.190910.002/V12.5.5.0.QFMCNXM:user/release-keys`.
Android version, security patch level and development signing keys are unchanged.
This property change alone does not establish a Play Integrity verdict.
The rebuilt GApps package was checked for the stock value across system, vendor,
product, system-ext, ODM, recovery, and OTA metadata. Its build log is
`build-gapps-stock-fingerprint-2.log`. Installation and integrity retesting are
pending phone reconnection. The earlier frame-synchronization fix remains in
this build. Device product-makefile dependencies invalidate cached property
outputs when the identity changes, avoiding Ruby's stale incremental properties.

Inspected firmware: `V12.5.5.0.QFMCNXM`, Android 10, September 2021 patch.
Evidence comes from its `rawprogram*.xml`, boot/recovery headers, DTBO, and vendor fstab.
Read-only fastboot inspection of the actual phone on 2026-11-17 confirmed
`product: laurus`, an unlocked bootloader, and all seven configured partition
sizes. Slot-query variables are unsupported by this bootloader. Nothing was
flashed, erased, booted, or rebooted during inspection.

- Single-slot partitions, with independent 64 MiB boot and recovery partitions.
- System-as-root, 5 GiB system, 1 GiB vendor, 512 MiB cache, 16 MiB metadata.
- DTBO partition is 24 MiB, although the supplied image is only 8 MiB.
- Boot header v2, 4096-byte pages, DTB address `0x01f00000`.
- Stock boot has no ramdisk; recovery has its own ramdisk.
- No `slotselect` in the vendor fstab, no dynamic partitions in the stock layout.

The port removes Mi A3 A/B postinstall, boot-control and update-engine packages,
enables separate recovery, and uses the laurus partition sizes and device assert.
Recovery has a separate fstab containing vendor and raw-partition mappings;
normal boot retains the kernel DT vendor mount.
The kernel overlay's early vendor mount also needs its A/B `slotselect` flag
removed; the patch adds recovery to its AVB partition list to match stock.
Three audio-driver header symlinks are made relative to the kernel itself;
the donor links assumed a checkout at `kernel/msm-4.14`.
The system-root AVB public-key directory has an explicit SELinux rootfs label.
The RMTFS shared-memory node also drops `qcom,vm-nav-path` to match the stock
CC9e DTB. The donor's extra NAV VM permission request was rejected by the secure
monitor during the first hardware test, before the modem's first storage read.
The latest UDFPS source uses one fullscreen RGBA buffer for the background mask
and sensor circle. A device-specific SurfaceFlinger hook changes panel HBM just
before presenting the frame that adds or removes that buffer, after its GPU
acquire fence is ready. The fingerprint HAL retains touch/sensor controls but no
longer independently changes panel HBM. This mode is selected by a device overlay;
other devices keep the original SystemUI behavior. The panel's original command
sequence and settling delays are retained. The coordinated build was installed
without wiping userdata. Its frame hook and device resource flag were verified
at runtime, and the owner confirmed no bright or dark flashes and working
fingerprint recognition during enrollment testing.
The vanilla build disables GMS. The GApps variant uses the original Ruby bundle
from its GitHub mirror at `b9f886167665e54ba8c7e0bcc5504c842c743ac4`:
https://github.com/ThankYouMario/ThankYouMario-proprietary_vendor_google_gms
Its LFS files are checked against their recorded SHA-256 hashes during download.
The trinket audio, display, media and GPS HALs use `ruby-nicobar`, matching the
Mi A3 product's original dependency selection. Roomservice has an empty laurus
dependency list because the local manifests manage these repositories explicitly.

## Remaining validation

The source-built kernel and Android 11 vendor baseline currently come from the
Mi A3 Ruby sources. Basic display output and Android startup work, but touch,
fingerprint, cameras, calls/mobile data, Wi-Fi, Bluetooth, audio and sensors
still need functional testing. Matching SoC and DT board IDs alone do not
establish hardware compatibility. The downloaded laurus Android 10
vendor dump is available locally for comparison; it is not blindly substituted
for the Android 11 vendor stack.

The Mi A3 fstab's Android 11 encryption settings are retained provisionally.
Do not assume existing MIUI userdata can be decrypted by this build.

The source-built kernel, boot image and DTBO compile successfully. The boot image
has header v2, 4096-byte pages, no ramdisk, Android 11 metadata and DTB address
`0x01f00000`. The DTBO has one overlay, no slot-selection flag, and includes
recovery in its AVB partition list. Both images fit the verified laurus partitions.
All 3,681 copied proprietary files were verified byte-identical to the Ruby donor.

## Prebuilt apps

The GApps variant replaces Camera Go with GCam `MGC_8.7.250_A11_V15a_snap.apk`
(`org.codeaurora.snapcam`). Both variants include IR Blaster
(`org.nslabs.ir_blaster`) as a regular system app.
`device/xiaomi/laurus/apps/fetch-apps.py` downloads GCam (SHA-256 pinned) and
the latest arm64 IR Blaster release into the device tree's `apps/prebuilt/`,
which Git ignores. APKs stay unmodified; compressed native libraries (GCam's)
are extracted beside the app, since Android does not extract them for system
apps. IR Blaster's libraries are stored uncompressed and load from the APK.
The updated GApps ROM was installed without formatting userdata. Android booted
and registered both packages as system apps, retaining the existing userdata
installations as system-app updates. The old Camera Go Play Store update was
still present in userdata and was disabled for the current user; its bundled APK
is absent from the GApps ROM.

Another Widget 2.3.3 (`com.tommasoberlose.anotherwidget`) is optional: it cannot
be downloaded automatically, and the build leaves it out when its APK is absent.
When present, the `LaurusLauncher` overlay puts it in place of At a Glance in the
default 4x4 and 5x5 layouts. The earlier Launcher3 migration patch is no longer applied, since there is no Launcher3 fork, so
an existing home screen keeps its At a Glance widget until the user replaces it.

Do not flash Mi A3 firmware, bootloaders, partition tables, or A/B conversion
packages as part of this port. The physical partition layout and bootloader state
were checked through fastboot; the connected phone is now running Android.

## Hardware test notes

The owner authorized recovery flashing, ROM installation, and a clean data reset.
Recovery, system, vendor, boot, DTBO and vbmeta have been installed. Recovery
reported successful OTA installation and formatting of data, cache and metadata.
The bootloader rejects `fastboot boot`; its `fastboot reboot recovery` command
appeared to start Android, while Power + Volume Up reliably entered recovery.
`adb reboot recovery` from recovery works.

The current block OTA writes system, vendor and boot. DTBO and vbmeta must be
installed separately from the same build; they are exported beside the ZIP.
Local hardware logs are under `stock/recovery-test/` and may contain identifiers.

The owner subsequently authorized a clean flash of the GApps variant. Recovery,
DTBO and vbmeta were updated, the corrected GApps OTA installed successfully,
and recovery confirmed formatting of data, cache and metadata. The APK-signature
check passed for all 37 imported Google apps with their original signers.
The clean-flashed GApps variant completed boot (`sys.boot_completed=1`), stopped
the boot animation, reported its modem baseband, and started Google Setup Wizard
and Play services. First boot spent roughly two minutes optimizing Google apps.
The UDFPS timing fix is included; the clean reset requires fingerprint enrollment
again before further biometric testing.

The first Android boot restarted after `Fatal error on modem!`. The earlier
kernel log showed `setup_shared_ram_perms: hyp_assign_phys failed` for the RMTFS
buffer. Removing the donor-only NAV VM request from the base DTBs resolved both
errors in the next boot; the donor modem-storage binary and physical modem
firmware were unchanged. Android completed boot and stopped the boot animation.
The exported OTA contains the same corrected kernel and DTBs tested on the phone;
packaging regenerates the boot image's AVB salt and build-fingerprint property.
The phone still has the initial recovery image; the exported recovery has also
been rebuilt with the corrected base DTBs. Initial artifacts are retained under
`artifacts/initial-build/` for comparison and are not the current test build.

## Original CAF release manifests

`caf-releases/` holds Qualcomm's original Ruby system and vendor release
manifests, retrieved from CodeLinaro's `clo/la/la/system/manifest` and
`clo/la/la/vendor/manifest` (branch `caf_migration/release`).
`pin-caf-revisions.py` turns them into `zz-caf-revisions.xml`, because many old
release tags did not survive the migration. Wayland and Trade Federation moved
to repositories with `_repo` suffixes that contain the same original commits.

Compare the configuration with a stock fastboot ROM:
`tools/check-layout.py /path/to/laurus_fastboot_firmware/images`.
