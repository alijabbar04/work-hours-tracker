[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Source setup is missing. Run: powershell -NoProfile -File .\setup.ps1"
}
& $venvPython (Join-Path $PSScriptRoot "app.py")
if ($LASTEXITCODE -ne 0) { throw "Work Hours Tracker exited with code $LASTEXITCODE. See the error above." }
