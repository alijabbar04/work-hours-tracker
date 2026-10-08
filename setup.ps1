# Install source dependencies into a project-local virtual environment.
[CmdletBinding()]
param(
    [switch]$CreateDesktopShortcut,
    [switch]$InstallDev,
    [string]$PythonExecutable = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot
if ($env:OS -ne "Windows_NT") { throw "This helper is for Windows. See README.md for manual source setup." }

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed (exit $LASTEXITCODE): $Executable" }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    if ($PythonExecutable) {
        Invoke-Checked $PythonExecutable @("-m", "venv", ".venv")
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        Invoke-Checked "py" @("-3", "-m", "venv", ".venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        Invoke-Checked "python" @("-m", "venv", ".venv")
    } else { throw "Install 64-bit Python 3.11-3.14 from https://www.python.org/downloads/windows/, then run setup again." }
}
Invoke-Checked $venvPython @("-c", "import struct,sys; assert (3,11) <= sys.version_info[:2] < (3,15), 'Python 3.11-3.14 required'; assert struct.calcsize('P') == 8, '64-bit Python required'; import tkinter")
$requirements = if ($InstallDev) { "requirements-dev.txt" } else { "requirements.txt" }
Invoke-Checked $venvPython @("-m", "pip", "install", "-r", $requirements)

if ($CreateDesktopShortcut) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "Work Hours Tracker (Source).lnk"
    if (Test-Path -LiteralPath $shortcutPath) {
        throw "Setup completed, but a shortcut already exists at $shortcutPath. It was left unchanged."
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
    $shortcut.Arguments = '"' + (Join-Path $PSScriptRoot "app.py") + '"'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.IconLocation = (Join-Path $PSScriptRoot "assets\icon.ico") + ",0"
    $shortcut.Description = "Log work hours, view timesheets and create invoices."
    $shortcut.Save()
    Write-Host "Desktop shortcut created." -ForegroundColor Green
}
Write-Host "Setup complete. Start with .\run.ps1" -ForegroundColor Green
