#!/usr/bin/env python3
"""Compare the bring-up configuration with an unmodified laurus fastboot ROM."""
import os
import argparse
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("images", type=Path)
parser.add_argument("--fastboot-report", type=Path)
args = parser.parse_args()
root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2])
device = root / "src/device/xiaomi/laurus"
board = (device / "BoardConfig.mk").read_text()
partitions = {}
for xml in sorted(args.images.glob("rawprogram[0-5].xml")):
    for entry in ET.parse(xml).getroot().findall("program"):
        partitions[entry.attrib["label"]] = int(entry.attrib["num_partition_sectors"]) * int(entry.attrib["SECTOR_SIZE_IN_BYTES"])
assert partitions, "No rawprogram XML files found"
variables = {
    "boot": "BOARD_BOOTIMAGE_PARTITION_SIZE",
    "recovery": "BOARD_RECOVERYIMAGE_PARTITION_SIZE",
    "dtbo": "BOARD_DTBOIMG_PARTITION_SIZE",
    "system": "BOARD_SYSTEMIMAGE_PARTITION_SIZE",
    "vendor": "BOARD_VENDORIMAGE_PARTITION_SIZE",
    "metadata": "BOARD_METADATAIMAGE_PARTITION_SIZE",
    "cache": "BOARD_CACHEIMAGE_PARTITION_SIZE",
}
for partition, variable in variables.items():
    match = re.search(rf"^{variable}\s*:=\s*(\S+)", board, re.M)
    assert match, f"Missing {variable}"
    size = int(match[1], 0)
    assert size == partitions[partition], f"{partition}: configured {size}, firmware {partitions[partition]}"
for variable in ("AB_OTA_UPDATER", "BOARD_USES_RECOVERY_AS_BOOT", "TARGET_NO_RECOVERY"):
    assert re.search(rf"^{variable}\s*:=\s*false\s*$", board, re.M), variable
assert not any(name.endswith(("_a", "_b")) for name in partitions), "Firmware has slotted partitions"
fstab = (device / "init/fstab.qcom").read_text()
assert "slotselect" not in fstab
recovery_fstab = (device / "init/recovery.fstab").read_text()
assert "slotselect" not in recovery_fstab
for partition in ("system", "vendor", "boot", "recovery", "cache", "dtbo", "vbmeta"):
    assert f"/by-name/{partition} " in recovery_fstab, f"Missing recovery fstab entry for {partition}"
for image in ("boot", "recovery"):
    with (args.images / f"{image}.img").open("rb") as source:
        header = source.read(1660)
    assert header[:8] == b"ANDROID!"
    assert struct.unpack_from("<I", header, 40)[0] == 2, "Unexpected boot header version"
    assert struct.unpack_from("<I", header, 36)[0] == 4096, "Unexpected boot page size"
    ramdisk_size = struct.unpack_from("<I", header, 16)[0]
    assert (ramdisk_size == 0) == (image == "boot"), "Unexpected stock ramdisk arrangement"
if args.fastboot_report:
    report = json.loads(args.fastboot_report.read_text())
    assert re.search(r"^product: laurus$", report["product"]["response"], re.M), "Connected phone is not laurus"
    assert re.search(r"^unlocked: yes$", report["unlocked"]["response"], re.M), "Bootloader is locked"
    for partition in variables:
        response = report[f"partition-size:{partition}"]["response"]
        match = re.search(rf"^partition-size:{partition}:\s*(0x[0-9a-fA-F]+)", response, re.M)
        assert match and int(match[1], 16) == partitions[partition], f"Actual {partition} partition differs from stock"
print(json.dumps({"status": "PASS", "layout": "single-slot, system-as-root, separate recovery", "partition_bytes": {name: partitions[name] for name in variables}}, indent=2))
