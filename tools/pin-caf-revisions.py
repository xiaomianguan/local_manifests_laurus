#!/usr/bin/env python3
"""Recover original release SHAs where migrated CodeAurora tags are missing."""
import os
import argparse
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(os.environ.get("LAURUS_ROOT") or Path(__file__).resolve().parents[2])
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("effective_manifest", type=Path)
args = parser.parse_args()
releases = {
    "caf_system": "LA.QSSI.11.0.r1-12300-qssi.0",
    "caf_vendor": "LA.UM.9.14.r1-16900-LAHAINA.0",
}
maps = {}
relocations = {
    "platform/external/wayland_repo": "platform/external/wayland",
    "platform/tools/tradefederation_repo": "platform/tools/tradefederation",
}
for remote, release in releases.items():
    tree = ET.parse(Path(__file__).resolve().parent / "caf-releases" / f"{release}.xml")
    maps[remote] = {p.attrib["name"]: p.attrib["revision"] for p in tree.getroot().findall("project")}
effective = ET.parse(args.effective_manifest).getroot()
default_remote = effective.find("default").attrib["remote"]
output = ET.Element("manifest")
output.append(ET.Comment(" Exact SHAs from Qualcomm's original Ruby system/vendor releases. "))
for project in effective.findall("project"):
    remote = project.get("remote", default_remote)
    if remote not in maps:
        continue
    name = project.attrib["name"]
    revision = maps[remote][relocations.get(name, name)]
    assert re.fullmatch(r"[0-9a-f]{40}", revision), (name, revision)
    ET.SubElement(output, "extend-project", name=name, revision=revision)
ET.indent(output, space="  ")
destination = root / "src/.repo/local_manifests/zz-caf-revisions.xml"
ET.ElementTree(output).write(destination, encoding="UTF-8", xml_declaration=True)
print(f"Pinned {len(output) - 1} CAF projects to original release commits")
