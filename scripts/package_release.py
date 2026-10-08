"""Package only the newly built executable and public documentation."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = {
    "dist/Work Hours Tracker.exe": "Work Hours Tracker.exe",
    "QUICK_START.txt": "QUICK_START.txt",
    "LICENSE": "LICENSE.txt",
    "PRIVACY.md": "PRIVACY.md",
    "THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md",
    "VERSION": "VERSION.txt",
}


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("VERSION must contain a stable version such as 1.0.0.")
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    members = dict(MEMBERS)
    license_dir = ROOT / "release-licenses"
    manifest_path = license_dir / "MANIFEST.json"
    if license_dir.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise SystemExit("Run scripts/collect_licenses.py before packaging.")
    names = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(names, list) or not names:
        raise SystemExit("Licence manifest must be a nonempty list.")
    for name in names:
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.txt", name):
            raise SystemExit("Unsafe licence manifest entry.")
        members[f"release-licenses/{name}"] = f"licenses/{name}"
    for relative in members:
        source = ROOT / relative
        if (not source.is_file() or source.is_symlink()
                or not source.resolve().is_relative_to(ROOT.resolve())):
            raise SystemExit(f"Missing or unsafe release input: {relative}")
    archive = output / f"Work-Hours-Tracker-{version}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, name in members.items():
            bundle.write(ROOT / relative, name)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="ascii"
    )
    with zipfile.ZipFile(archive) as bundle:
        if set(bundle.namelist()) != set(members.values()) or bundle.testzip():
            raise SystemExit("Release archive validation failed.")
    print(f"Created {archive.name} ({archive.stat().st_size:,} bytes)")
    print(f"SHA256 {checksum}")


if __name__ == "__main__":
    main()
