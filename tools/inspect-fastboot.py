#!/usr/bin/env python3
"""Read a single connected phone's bootloader variables without changing state."""
import os
from pathlib import Path
import json
import subprocess

devices = subprocess.run(["fastboot", "devices"], capture_output=True, text=True, check=True)
serials = [line.split()[0] for line in devices.stdout.splitlines() if line.strip()]
if len(serials) != 1:
    raise SystemExit(f"Expected one fastboot device, found {len(serials)}; no commands sent")
serial = serials[0]
variables = ["product", "unlocked", "secure", "current-slot", "slot-count", "anti"]
for name in ("boot", "recovery", "system", "vendor", "dtbo", "vbmeta", "cache", "metadata"):
    variables += [f"has-slot:{name}", f"partition-size:{name}", f"partition-type:{name}"]
report = {}
for variable in variables:
    try:
        result = subprocess.run(["fastboot", "-s", serial, "getvar", variable], capture_output=True, text=True, timeout=15)
        output = (result.stdout + result.stderr).replace(serial, "<device>")
        # Some fastboot versions return zero even when the bootloader rejects a variable.
        report[variable] = {"exit_code": result.returncode, "supported": result.returncode == 0 and "FAILED" not in output, "response": output.strip()}
    except subprocess.TimeoutExpired:
        report[variable] = {"error": "timeout; inspection stopped"}
        break
root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2])
destination = root / "stock/fastboot-info.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
