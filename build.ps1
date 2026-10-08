# Build and package a clean Windows x64 release. Never installs over a desktop app.
[CmdletBinding()]
param([string]$PythonExecutable = "")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot
if ($env:OS -ne "Windows_NT") { throw "The Windows release must be built on Windows." }

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $Executable" }
}

$buildPython = Join-Path $PSScriptRoot ".build-venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $buildPython)) {
    if ($PythonExecutable) {
        Invoke-Checked $PythonExecutable @("-m", "venv", ".build-venv")
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked "py" @("-3", "-m", "venv", ".build-venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        Invoke-Checked "python" @("-m", "venv", ".build-venv")
    } else { throw "Install 64-bit Python 3.11-3.14 from python.org, then run this script again." }
}
Invoke-Checked $buildPython @("-c", "import struct,sys; assert (3,11) <= sys.version_info[:2] < (3,15), 'Python 3.11-3.14 required'; assert struct.calcsize('P') == 8, '64-bit Python required'")
Invoke-Checked $buildPython @("-m", "pip", "install", "-r", "requirements-dev.txt")

# Tests and builds must not discover an installed user's data directory.
$previousDataDir = $env:WORK_HOURS_TRACKER_DATA_DIR
try {
    $env:WORK_HOURS_TRACKER_DATA_DIR = Join-Path $PSScriptRoot "build\test-data"
    Invoke-Checked $buildPython @("-m", "pytest", "tests", "-q")
    Invoke-Checked $buildPython @("make_icon.py")
    Invoke-Checked $buildPython @("-m", "PyInstaller", "--noconfirm", "--clean", "Work Hours Tracker.spec")
    Invoke-Checked $buildPython @("scripts\collect_licenses.py")
    Invoke-Checked $buildPython @("scripts\package_release.py")
} finally {
    $env:WORK_HOURS_TRACKER_DATA_DIR = $previousDataDir
}
Write-Host "Release ZIP and SHA256 checksum are in release\." -ForegroundColor Green
