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

$venvPython = ".\.venv\Scripts\python.exe"
Write-Host "[2/3] Preparing pip and installing dependencies..."
Write-Host "Using the official Python Package Index (PyPI); no third-party mirror is configured." -ForegroundColor DarkGray

# Upgrade pip when possible, but don't block installation if the current pip is usable.
& $venvPython -m pip install --upgrade pip --index-url https://pypi.org/simple --retries 2 --timeout 20
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not upgrade pip. Continuing with the version already installed."
}

& $venvPython -m pip install -r requirements.txt --index-url https://pypi.org/simple --retries 4 --timeout 30
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Dependency installation failed. This is usually a network/proxy/firewall issue, not a China-specific setting in this script." -ForegroundColor Red
    Write-Host "Check that https://pypi.org and https://files.pythonhosted.org open in your browser, then retry." -ForegroundColor Yellow
    Write-Host "If your network requires a proxy, configure the correct proxy for pip; do not disable HTTPS certificate checks." -ForegroundColor Yellow
    throw "Could not install Python dependencies. See the pip error above."
}

Write-Host "[3/3] Launching dashboard..."
& $venvPython run.py
