$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host ""
Write-Host " CryptoPulse - Windows setup" -ForegroundColor Cyan
Write-Host " ---------------------------" -ForegroundColor DarkCyan

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $pythonCommand = "py"; $pythonArgs = @("-3") }
else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3.10+ was not found. Install Python from https://www.python.org/downloads/windows/ and retry." }
    $pythonCommand = "python"; $pythonArgs = @()
}
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[1/3] Creating virtual environment..."
    & $pythonCommand @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create Python virtual environment." }
} else { Write-Host "[1/3] Virtual environment already exists." }

Write-Host "[2/3] Installing dependencies..."
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

Write-Host "[3/3] Launching dashboard..."
& ".\.venv\Scripts\python.exe" run.py
