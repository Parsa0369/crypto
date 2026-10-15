param(
    [Parameter(Position = 0)]
    [ValidateSet("open")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Register "open" in the user's PowerShell profile for future terminals.
try {
    $profilePath = $PROFILE.CurrentUserAllHosts
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) { New-Item -ItemType Directory -Path $profileDir -Force | Out-Null }
    if (-not (Test-Path $profilePath)) { New-Item -ItemType File -Path $profilePath -Force | Out-Null }
    $profileText = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($profileText -notmatch '# CryptoPulse open command') {
        $projectScript = (Join-Path $PSScriptRoot 'start.ps1').Replace("'", "''")
        Add-Content -Path $profilePath -Encoding UTF8 -Value @"

# CryptoPulse open command
function global:open { & '$projectScript' open }
"@
    }
} catch { }

function Invoke-QuietProcess([string]$File, [string[]]$Arguments, [string]$Message, [string]$LogPath) {
    Remove-Item $LogPath -Force -ErrorAction SilentlyContinue
    $errorLog = "$LogPath.err"
    Remove-Item $errorLog -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru -NoNewWindow -RedirectStandardOutput $LogPath -RedirectStandardError $errorLog
    $frames = @('◜','◠','◝','◞','◡','◟')
    $i = 0
    while (-not $process.HasExited) {
        Write-Host ("  {0}  {1}   " -f $frames[$i % $frames.Count], $Message) -NoNewline -ForegroundColor Cyan
        Start-Sleep -Milliseconds 110
        Write-Host ([char]13) -NoNewline
        $i++
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) {
        Write-Host ""
        if (Test-Path $LogPath) { Get-Content $LogPath -Tail 12 | Write-Host }
        if (Test-Path $errorLog) { Get-Content $errorLog -Tail 12 | Write-Host }
        throw "$Message failed. Details are shown above."
    }
    Write-Host ("  ✦  {0}   " -f $Message) -ForegroundColor Green
}

Write-Host ""
Write-Host "      .----------------------." -ForegroundColor DarkCyan
Write-Host "      |   C R Y P T O P U L S E  |" -ForegroundColor Cyan
Write-Host "      '----------------------'" -ForegroundColor DarkCyan
Write-Host "            ◆  MARKET LAB" -ForegroundColor Magenta
Write-Host ""

if ($Command -eq "open") {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git for Windows is required for the open command." }
    Invoke-QuietProcess -File (Get-Command git).Source -Arguments @("pull","--ff-only") -Message "Syncing GitHub" -LogPath (Join-Path $env:TEMP "cryptopulse-git.log")
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) { $pythonCommand = "py"; $pythonArgs = @("-3") }
else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3.10+ was not found. Install Python, then retry." }
    $pythonCommand = "python"; $pythonArgs = @()
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  ✦ Preparing CryptoPulse..." -ForegroundColor Cyan
    & $pythonCommand @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create Python virtual environment." }
}

$venvPython = (Resolve-Path ".venv\Scripts\python.exe").Path
$logPath = Join-Path $env:TEMP "cryptopulse-install.log"
Invoke-QuietProcess -File $venvPython -Arguments @("-m","pip","install","-r","requirements.txt","--retries","4","--timeout","60","--disable-pip-version-check","-q") -Message "Preparing modules" -LogPath $logPath

Write-Host ""
Write-Host "  ✦ Launching CryptoPulse..." -ForegroundColor Magenta
& $venvPython run.py
