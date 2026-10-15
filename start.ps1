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
$packageIndex = "https://mirrors.aliyun.com/pypi/simple/"
Write-Host "[2/3] Preparing pip and installing dependencies..."
Write-Host "Using the Aliyun PyPI mirror: $packageIndex" -ForegroundColor DarkGray

# Upgrade pip when possible, but don't block installation if the current pip is usable.
& $venvPython -m pip install --upgrade pip --index-url $packageIndex --retries 5 --timeout 120
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Could not upgrade pip from the Aliyun mirror. Continuing with the version already installed."
}

& $venvPython -m pip install -r requirements.txt --index-url $packageIndex --retries 5 --timeout 120
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Dependency installation failed using the Aliyun PyPI mirror." -ForegroundColor Red
    Write-Host "Check your internet connection and whether https://mirrors.aliyun.com/pypi/simple/ is reachable, then retry." -ForegroundColor Yellow
    Write-Host "If your network requires a proxy, configure the correct proxy for pip; do not disable HTTPS certificate checks." -ForegroundColor Yellow
    throw "Could not install Python dependencies. See the pip error above."
}

Write-Host "[3/3] Launching dashboard..."
& $venvPython run.py
