#!/usr/bin/env python3
"""Reject common Mi A3 packaging mistakes before testing a laurus build."""
import os
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("product_out", type=Path)
parser.add_argument("--ota", type=Path, required=True)
parser.add_argument("--gapps", action="store_true", help="Require core Google apps and their permission grants")
args = parser.parse_args()
root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2])
board = (root / "src/device/xiaomi/laurus/BoardConfig.mk").read_text()
product = (root / "src/device/xiaomi/laurus/pa_laurus.mk").read_text()
fingerprint = re.search(r"^BUILD_FINGERPRINT\s*:=\s*(\S+)", product, re.M)
if fingerprint:
    expected = fingerprint[1]
    for relative in ("system/build.prop", "system/product/build.prop",
                     "system/system_ext/build.prop", "vendor/build.prop",
                     "vendor/odm/etc/build.prop", "recovery/root/prop.default"):
        props = (args.product_out / relative).read_text().splitlines()
        values = [line.split("=", 1)[1] for line in props
                  if "=" in line and line.split("=", 1)[0].endswith("build.fingerprint")]
        assert values and all(value == expected for value in values), f"Stale fingerprint in {relative}"
    print("PASS: stock device fingerprint is consistent across generated partition/recovery properties")
for image, variable in {
    "system": "BOARD_SYSTEMIMAGE_PARTITION_SIZE",
    "vendor": "BOARD_VENDORIMAGE_PARTITION_SIZE",
}.items():
    path = args.product_out / f"{image}.img"
    limit = int(re.search(rf"^{variable}\s*:=\s*(\S+)", board, re.M)[1], 0)
    with path.open("rb") as stream:
        header = stream.read(28)
    if struct.unpack_from("<I", header)[0] == 0xED26FF3A:
        block_size, total_blocks = struct.unpack_from("<II", header, 12)
        expanded_size = block_size * total_blocks
    else:
        expanded_size = path.stat().st_size
    assert 0 < expanded_size <= limit, f"{path}: expanded image exceeds physical partition"
for image, variable in {
    "boot": "BOARD_BOOTIMAGE_PARTITION_SIZE",
    "recovery": "BOARD_RECOVERYIMAGE_PARTITION_SIZE",
    "dtbo": "BOARD_DTBOIMG_PARTITION_SIZE",
}.items():
    path = args.product_out / f"{image}.img"
    limit = int(re.search(rf"^{variable}\s*:=\s*(\S+)", board, re.M)[1], 0)
    assert 0 < path.stat().st_size <= limit, f"{path}: invalid image size"
    if image in ("boot", "recovery"):
        with path.open("rb") as stream:
            header = stream.read(1660)
        assert header[:8] == b"ANDROID!", path
        assert struct.unpack_from("<I", header, 40)[0] == 2, path
        ramdisk_size = struct.unpack_from("<I", header, 16)[0]
        assert (ramdisk_size == 0) == (image == "boot"), f"{path}: unexpected ramdisk"
        if image == "boot":
            kernel_size = struct.unpack_from("<I", header, 8)[0]
            second_size = struct.unpack_from("<I", header, 24)[0]
            page_size = struct.unpack_from("<I", header, 36)[0]
            recovery_dtbo_size = struct.unpack_from("<I", header, 1632)[0]
            dtb_size = struct.unpack_from("<I", header, 1648)[0]
            aligned = lambda size: ((size + page_size - 1) // page_size) * page_size
            dtb_offset = page_size + sum(map(aligned, (
                kernel_size, ramdisk_size, second_size, recovery_dtbo_size)))
            with path.open("rb") as stream:
                stream.seek(dtb_offset)
                dtbs = stream.read(dtb_size)
            assert dtb_size > 0 and len(dtbs) == dtb_size, "Missing boot DTBs"
            assert dtbs[:4] == bytes.fromhex("d00dfeed"), "Invalid boot DTB"
            assert b"qcom,vm-nav-path" not in dtbs, "Incompatible RMTFS NAV memory request"
            with path.open("rb") as stream:
                boot_payload = stream.read(dtb_offset + dtb_size)
        if image == "recovery":
            assert struct.unpack_from("<I", header, 1632)[0] > 0, "Recovery DTBO is missing"
    else:
        content = path.read_bytes()
        assert content[:4] == bytes.fromhex("d7b7ab1e"), "Invalid DTBO table"
        assert b"slotselect" not in content, "DTBO still requests A/B slots"
        assert b"vbmeta,boot,recovery,system,vendor,dtbo" in content, "Wrong DTBO AVB partition list"
with zipfile.ZipFile(args.ota) as ota:
    assert ota.testzip() is None, "OTA archive CRC check failed"
    assert ota.read("boot.img")[:len(boot_payload)] == boot_payload, "OTA boot payload differs from validated image"
    assert "payload.bin" not in ota.namelist(), "This is an A/B OTA"
    metadata = ota.read("META-INF/com/android/metadata").decode()
    assert "ota-type=BLOCK" in metadata, "Expected a non-A/B block OTA"
    assert "pre-device=laurus" in metadata, "OTA device is not laurus"
    if fingerprint:
        assert f"post-build={fingerprint[1]}\n" in metadata + "\n", "OTA metadata has a stale fingerprint"
    updater = ota.read("META-INF/com/google/android/updater-script").decode()
    assert "laurel_sprout" not in updater, "Updater still targets Mi A3"
    assert "laurus" in updater, "Missing laurus device guard"
system = args.product_out / "system"
prebuilt = root / "src/device/xiaomi/laurus/apps/prebuilt"
has_widget = (prebuilt / "LaurusAnotherWidget.apk").is_file()
apps = ["LaurusIRBlaster"] + (["LaurusAnotherWidget"] if has_widget else []) + (["LaurusGCam"] if args.gapps else [])
for name in apps:
    path = system / f"product/app/{name}/{name}.apk"
    assert path.read_bytes() == (prebuilt / f"{name}.apk").read_bytes(), f"Prebuilt APK was altered: {name}"
    with zipfile.ZipFile(path) as apk:
        assert apk.testzip() is None, f"Corrupt prebuilt APK: {name}"
        for entry in apk.infolist():
            if (entry.filename.startswith("lib/arm64-v8a/") and entry.filename.endswith(".so")
                    and entry.compress_type != zipfile.ZIP_STORED):
                installed = path.parent / "lib/arm64" / Path(entry.filename).name
                assert installed.read_bytes() == apk.read(entry), f"Missing/altered JNI: {name} {entry.filename}"
launcher_overlay = system / "system_ext/overlay/LaurusLauncher.apk"
if has_widget:
    aapt = root / "src/out/host/linux-x86/bin/aapt2"
    for layout in ("default_workspace_4x4.xml", "default_workspace_5x5.xml"):
        compiled = subprocess.check_output([str(aapt), "dump", "xmltree", "--file",
                                           f"res/xml/{layout}", str(launcher_overlay)], text=True)
        assert "com.tommasoberlose.anotherwidget.ui.widgets.MainWidget" in compiled, layout
        assert "SmartspaceWidgetProvider" not in compiled, layout
else:
    assert not (system / "product/app/LaurusAnotherWidget").exists(), "Stale Another Widget installed"
    assert not launcher_overlay.exists(), "Launcher overlay installed without Another Widget"
print("PASS: prebuilt apps " + ", ".join(apps) + (" and launcher layout overlay" if has_widget else ""))
if args.gapps:
    assert not (system / "product/app/GoogleCameraGo").exists(), "Camera Go was not replaced"
    system = args.product_out / "system"
    for relative in (
        "product/priv-app/GmsCore/GmsCore.apk",
        "product/priv-app/Phonesky/Phonesky.apk",
        "system_ext/priv-app/GoogleServicesFramework/GoogleServicesFramework.apk",
        "system_ext/priv-app/SetupWizard/SetupWizard.apk",
    ):
        with zipfile.ZipFile(system / relative) as apk:
            assert "AndroidManifest.xml" in apk.namelist(), relative
            assert apk.testzip() is None, f"Corrupt APK: {relative}"
    permissions = system / "product/etc/permissions/privapp-permissions-google-product.xml"
    assert 'package="com.google.android.gms"' in permissions.read_text(), "Missing Play services permission grants"
    assert "ro.com.google.gmsversion=11_202106" in (system / "product/build.prop").read_text(), "GMS configuration missing"
    print("PASS: Google Play services, Play Store, Services Framework, Setup Wizard and GMS configuration")
print("PASS: single-slot boot/recovery/DTBO headers and laurus block OTA metadata")
