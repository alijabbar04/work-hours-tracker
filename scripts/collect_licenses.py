"""Collect upstream licence documents, without build paths or private metadata."""
from __future__ import annotations

import importlib.metadata
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-") or "license"


def collect(output: Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError("Licence output must not be a symlink.")
    names = []

    def save(name: str, text: str) -> None:
        target = output / name
        if target.is_symlink():
            raise ValueError("Refusing to overwrite a symlink in licence output.")
        target.write_text(text, encoding="utf-8")
        names.append(name)

    for distribution in sorted(
        importlib.metadata.distributions(),
        key=lambda item: item.metadata.get("Name", "").lower(),
    ):
        name = distribution.metadata.get("Name", "Unnamed")
        label = safe_name(f"{name}-{distribution.version}")
        index = 0
        for entry in distribution.files or []:
            basename = entry.name.lower()
            if not basename.startswith(("license", "licence", "copying", "notice")):
                continue
            metadata_license = any(part.endswith(".dist-info") for part in entry.parts)
            font_license = name.lower() == "matplotlib" and "fonts" in entry.parts
            pyinstaller_license = name.lower() == "pyinstaller" and basename.startswith("copying")
            if not (metadata_license or font_license or pyinstaller_license):
                continue
            source = Path(distribution.locate_file(entry))
            if not source.is_file() or source.is_symlink():
                continue
            index += 1
            text = source.read_text(encoding="utf-8", errors="replace")
            save(f"{label}-{index}-{safe_name(entry.name)}.txt", f"{name} {distribution.version}\n\n{text}\n")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file() or python_license.is_symlink():
        raise ValueError("The Python installation must include LICENSE.txt.")
    python_text = python_license.read_text(encoding="utf-8", errors="replace")
    save(f"Python-{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}-LICENSE.txt", python_text)
    for component, relative in (
        ("Tcl", "tcl/tcl8.6/license.terms"),
        ("Tk", "tcl/tk8.6/license.terms"),
    ):
        source = Path(sys.base_prefix) / relative
        if source.is_file() and not source.is_symlink():
            text = source.read_text(encoding="utf-8", errors="replace")
        elif "Scriptics Corporation" in python_text:
            # Some official Python Windows builds embed both Tcl/Tk terms in
            # LICENSE.txt rather than retaining a separate Tcl licence file.
            text = "Tcl/Tk terms included in the Python runtime licence:\n\n" + python_text
        else:
            raise ValueError(f"Missing licence terms for {component}.")
        save(f"{component}-LICENSE.txt", text)
    manifest = output / "MANIFEST.json"
    if manifest.is_symlink():
        raise ValueError("Licence manifest must not be a symlink.")
    manifest.write_text(json.dumps(sorted(names), indent=2) + "\n", encoding="utf-8")
    return names


if __name__ == "__main__":
    files = collect(ROOT / "release-licenses")
    print(f"Collected {len(files)} upstream licence documents.")
