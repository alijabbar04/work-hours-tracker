"""Only upstream licence documents enter the release licence manifest."""
import importlib.util
import json
from pathlib import Path, PurePosixPath


spec = importlib.util.spec_from_file_location(
    "collect_licenses", Path(__file__).resolve().parents[1] / "scripts" / "collect_licenses.py"
)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class SyntheticDistribution:
    metadata = {"Name": "matplotlib"}
    version = "1.0.0"
    files = [
        PurePosixPath("matplotlib-1.0.0.dist-info/licenses/LICENSE"),
        PurePosixPath("matplotlib/mpl-data/fonts/ttf/LICENSE_FONT"),
        PurePosixPath("matplotlib-1.0.0.dist-info/direct_url.json"),
    ]

    def __init__(self, root):
        self.root = root

    def locate_file(self, entry):
        return self.root / str(entry)


def test_collects_package_font_runtime_licenses_without_private_metadata(tmp_path, monkeypatch):
    distribution = SyntheticDistribution(tmp_path)
    for entry in distribution.files:
        path = distribution.locate_file(entry)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Private local path" if entry.name == "direct_url.json" else "Synthetic licence terms", encoding="utf-8")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    # Python Windows distributions may embed Tcl/Tk terms without a Tcl file.
    (runtime / "LICENSE.txt").write_text("Synthetic runtime terms: Scriptics Corporation", encoding="utf-8")
    monkeypatch.setattr(collector.importlib.metadata, "distributions", lambda: [distribution])
    monkeypatch.setattr(collector.sys, "base_prefix", str(runtime))
    output = tmp_path / "collected"
    names = collector.collect(output)
    assert len(names) == 5  # package, font, Python, Tcl and Tk
    assert names == json.loads((output / "MANIFEST.json").read_text()) or sorted(names) == json.loads((output / "MANIFEST.json").read_text())
    assert any("FONT" in name for name in names)
    assert all("Private local path" not in (output / name).read_text() for name in names)
    assert all("direct_url" not in name for name in names)
