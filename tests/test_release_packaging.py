"""Release packages must never pick up arbitrary runtime files."""
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "package_release", Path(__file__).resolve().parents[1] / "scripts" / "package_release.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def prepare(root):
    (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    for relative in package.MEMBERS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic public input")
    # VERSION is one of the public members.
    (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    licenses = root / "release-licenses"
    licenses.mkdir()
    (licenses / "Example-1.0-LICENSE.txt").write_text("Synthetic license", encoding="utf-8")
    (licenses / "MANIFEST.json").write_text(json.dumps(["Example-1.0-LICENSE.txt"]), encoding="utf-8")


def test_package_whitelist_and_checksum(tmp_path, monkeypatch):
    prepare(tmp_path)
    (tmp_path / "config.json").write_text('{"name":"Do not publish"}', encoding="utf-8")
    (tmp_path / "release-licenses" / "stale-private.txt").write_text("Do not publish", encoding="utf-8")
    monkeypatch.setattr(package, "ROOT", tmp_path)
    package.main()
    archive = tmp_path / "release" / "Work-Hours-Tracker-1.0.0-windows-x64.zip"
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(package.MEMBERS.values()) | {"licenses/Example-1.0-LICENSE.txt"}
        assert all(b"Do not publish" not in bundle.read(name) for name in bundle.namelist())
    assert archive.with_suffix(".zip.sha256").read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_package_rejects_license_path_traversal(tmp_path, monkeypatch):
    prepare(tmp_path)
    (tmp_path / "release-licenses" / "MANIFEST.json").write_text(json.dumps(["../private.txt"]), encoding="utf-8")
    monkeypatch.setattr(package, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="Unsafe licence"):
        package.main()


def test_package_rejects_missing_executable(tmp_path, monkeypatch):
    prepare(tmp_path)
    (tmp_path / "dist" / "Work Hours Tracker.exe").unlink()
    monkeypatch.setattr(package, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="Missing or unsafe"):
        package.main()
