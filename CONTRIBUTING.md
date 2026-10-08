# Contributing

Small, focused fixes and suggestions are welcome. Open an issue with a reproducible example or submit a pull request explaining the user-visible change.

## Local development

Use 64-bit Python 3.11–3.14. On Windows:

```powershell
powershell -NoProfile -File .\setup.ps1 -InstallDev
$env:WORK_HOURS_TRACKER_DATA_DIR = Join-Path $env:TEMP 'work-hours-tracker-development'
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe app.py
```

The separate data folder keeps development launches away from your installed tracker. Tests should use temporary directories and synthetic fixtures. Do not run examples against a personal workbook.

Application startup/navigation lives in `app.py`. Storage, invoices and configuration live in `core/`; Tkinter views live in `ui/`. Keep UI work on the Tk thread and show actionable errors for storage or network failures.

## Before a pull request

- Run the relevant tests and the complete existing suite.
- Check first launch with an empty data folder.
- Keep cloud exports and network features opt-in.
- Use invented names, dates, rates and summaries in tests. Never commit real workbooks, PDFs, configuration, keys or generated mobile HTML.
- Describe what changed and how you verified it. For visible UI changes, share screenshots using synthetic data.

The MIT licence covers contributions to the application. Dependencies retain their own licences.

## Release checklist

1. Update `VERSION`, the changelog and any versioned download examples.
2. Build on Windows using `powershell -NoProfile -File .\build.ps1`. The script creates an isolated build environment and runs tests before packaging.
3. Smoke-test the new executable with `WORK_HOURS_TRACKER_DATA_DIR` pointing to a fresh temporary folder. Check onboarding, save/edit, workbook backups and invoice generation with synthetic details.
4. Inspect the source changes and release ZIP for private data. Packaging uses an explicit allowlist; never add runtime folders to it.
5. Verify the ZIP's SHA256 and licence documents, then push the matching version tag, for example `v1.0.0`.

The tagged Windows workflow verifies that the tag matches `VERSION`, builds and creates a release. CI uses pinned GitHub actions and grants release-writing permission only to the release job. Published executables are unsigned unless a future release documents otherwise.
