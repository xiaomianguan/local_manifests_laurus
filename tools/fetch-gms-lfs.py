#!/usr/bin/env python3
"""Fetch Ruby GMS LFS files without requiring a host git-lfs installation."""
import os
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2]) / "src/vendor/google/gms"
if not (root / "config.mk").is_file():
    raise SystemExit("GMS sources missing; run tools/sync.sh vendor/google/gms")
objects = {}
for path in root.rglob("*"):
    if not path.is_file() or ".git" in path.parts or path.stat().st_size > 1024:
        continue
    content = path.read_bytes()
    if content.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        fields = dict(line.split(" ", 1) for line in content.decode().splitlines()[1:])
        oid = fields["oid"].removeprefix("sha256:")
        obj = objects.setdefault(oid, {"oid": oid, "size": int(fields["size"]), "paths": []})
        obj["paths"].append(path)
if not objects:
    print("GMS LFS: no unresolved pointers")
    raise SystemExit(0)
request = urllib.request.Request(
    "https://github.com/ThankYouMario/ThankYouMario-proprietary_vendor_google_gms.git/info/lfs/objects/batch",
    data=json.dumps({"operation": "download", "transfers": ["basic"],
                     "objects": [{"oid": x["oid"], "size": x["size"]} for x in objects.values()]}).encode(),
    headers={"Content-Type": "application/vnd.git-lfs+json", "Accept": "application/vnd.git-lfs+json"},
)
with urllib.request.urlopen(request, timeout=60) as response:
    entries = json.load(response)["objects"]

def download(entry):
    obj = objects[entry["oid"]]
    if "error" in entry:
        raise RuntimeError(f"GMS LFS object unavailable: {entry['oid']}")
    action = entry["actions"]["download"]
    req = urllib.request.Request(action["href"], headers=action.get("header", {}))
    target = obj["paths"][0]
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary = Path(output.name)
            digest = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(req, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        if size != obj["size"] or digest.hexdigest() != obj["oid"]:
            raise RuntimeError(f"GMS LFS integrity failure: {target.relative_to(root)}")
        content = temporary.read_bytes() if len(obj["paths"]) > 1 else None
        temporary.chmod(target.stat().st_mode & 0o777)
        temporary.replace(target)
        for duplicate in obj["paths"][1:]:
            duplicate.write_bytes(content)
        print(f"Verified {target.relative_to(root)} ({size} bytes)", flush=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

print(f"GMS LFS: fetching {len(objects)} objects ({sum(x['size'] for x in objects.values())} bytes)", flush=True)
with ThreadPoolExecutor(max_workers=4) as executor:
    list(executor.map(download, entries))
