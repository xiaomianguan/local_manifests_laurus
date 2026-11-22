#!/usr/bin/env python3
"""Verify installed Ruby Google APK signatures on API 30 and compare their signers to the source."""
import os
from pathlib import Path
import re
import subprocess

root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2])
source = root / "src/vendor/google/gms"
system = root / "src/out/target/product/laurus/system"
command = [str(Path(__file__).resolve().parent / "enter-build-env.sh"),
           "prebuilts/jdk/jdk11/linux-x86/bin/java", "--class-path",
           "prebuilts/sdk/tools/windows/lib/apksigner.jar", f"/workspace/{(Path(__file__).resolve().parent / 'VerifyGapps.java').relative_to(root)}"]
count = 0
for block in re.findall(r"android_app_import \{(.*?)\n\}", (source / "Android.bp").read_text(), re.S):
    name = re.search(r'name:\s*"([^"]+)"', block)[1]
    apk = re.search(r'apk:\s*"([^"]+)"', block)[1]
    partition = "product" if "product_specific: true" in block else (
        "system_ext" if "system_ext_specific: true" in block else "")
    app_dir = "priv-app" if "privileged: true" in block else "app"
    installed = system / partition / app_dir / name / f"{name}.apk"
    if not installed.is_file():
        raise SystemExit(f"Missing GMS APK: {installed.relative_to(root)}")
    command.extend((f"/workspace/{(source / apk).relative_to(root)}",
                    f"/workspace/{installed.relative_to(root)}"))
    count += 1
if not count:
    raise SystemExit("No GMS APK definitions found")
subprocess.run(command, check=True)
print(f"PASS: {count} Google APK signatures verified; original signers preserved")
