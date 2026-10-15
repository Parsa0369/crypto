param(
    [Parameter(Position = 0)]
    [ValidateSet("open", "panel")]
    [string]$Command
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Install/update shortcut commands in the current session and future PowerShell sessions.
$projectScript = (Join-Path $PSScriptRoot "start.ps1").Replace("'", "''")
$profileBlock = @"
# CryptoPulse command shortcuts - managed by start.ps1
function global:open { & '$projectScript' open }
function global:panel { & '$projectScript' panel }
# End CryptoPulse command shortcuts
"@

try {
    $profilePath = $PROFILE.CurrentUserAllHosts
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    if (-not (Test-Path $profilePath)) {
        New-Item -ItemType File -Path $profilePath -Force | Out-Null
    }

    $profileText = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($null -eq $profileText) { $profileText = "" }

    # Remove the earlier open-only registration and any previously managed block.
    $profileText = [regex]::Replace(
        $profileText,
        '(?ms)\r?\n?# CryptoPulse command shortcuts - managed by start\.ps1.*?# End CryptoPulse command shortcuts\r?\n?',
        "`r`n"
    )
    $profileText = [regex]::Replace(
        $profileText,
        '(?m)^# CryptoPulse open command\r?\nfunction global:open \{[^\r\n]*\}\r?\n?',
        ''
    )

    $profileText = $profileText.TrimEnd() + "`r`n`r`n" + $profileBlock + "`r`n"
    Set-Content -Path $profilePath -Value $profileText -Encoding UTF8
} catch {
    # Launching still works even if the profile is read-only or unavailable.
}

# Make the shortcuts available immediately in this PowerShell window too.
try {
    Set-Item -Path Function:global:open -Value ([scriptblock]::Create("& '$projectScript' open"))
    Set-Item -Path Function:global:panel -Value ([scriptblock]::Create("& '$projectScript' panel"))
} catch { }

function Invoke-QuietProcess(
    [string]$File,
    [string[]]$Arguments,
    [string]$Message,
    [string]$LogPath,
    [int]$MaxAttempts = 1,
    [switch]$SuppressFailureOutput
) {
    $errorLog = "$LogPath.err"
    $frames = @('◜','◠','◝','◞','◡','◟')

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        Remove-Item $LogPath, $errorLog -Force -ErrorAction SilentlyContinue
        $process = Start-Process -FilePath $File -ArgumentList $Arguments -PassThru -NoNewWindow -RedirectStandardOutput $LogPath -RedirectStandardError $errorLog
        $i = 0

        while (-not $process.HasExited) {
            $suffix = if ($MaxAttempts -gt 1) { " (try $attempt/$MaxAttempts)" } else { "" }
            Write-Host ("  {0}  {1}{2}   " -f $frames[$i % $frames.Count], $Message, $suffix) -NoNewline -ForegroundColor Cyan
            Start-Sleep -Milliseconds 120
            Write-Host ([char]13) -NoNewline
            $i++
            $process.Refresh()
        }

        $process.Refresh()
        if ($process.ExitCode -eq 0) {
            Write-Host ("  ✦  {0}   " -f $Message) -ForegroundColor Green
            return
        }

        if ($attempt -lt $MaxAttempts) {
            Write-Host ("  ↻  Retrying {0}..." -f $Message) -ForegroundColor Yellow
            Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 4))
        }
    }

    if (-not $SuppressFailureOutput) {
        Write-Host ""
        if (Test-Path $LogPath) { Get-Content $LogPath -Tail 10 | Write-Host }
        if (Test-Path $errorLog) { Get-Content $errorLog -Tail 14 | Write-Host }
    }
    throw "$Message failed after $MaxAttempts attempt(s)."
}

Write-Host ""
Write-Host "  ▄█▀▀█▄  CRYPTOPULSE  ▄█▀▀█▄" -ForegroundColor Cyan
Write-Host "  ▀▄▄▄▄▀   MARKET LAB   ▀▄▄▄▄▀" -ForegroundColor DarkCyan
Write-Host ""

# 'open' is the update-and-launch command. 'panel' skips GitHub sync for a quicker start.
if ($Command -eq "open") {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git for Windows is required for 'open'. Use 'panel' to start the local copy."
    }
    try {
        Invoke-QuietProcess -File (Get-Command git).Source -Arguments @("pull", "--ff-only") -Message "Syncing GitHub" -LogPath (Join-Path $env:TEMP "cryptopulse-git.log") -MaxAttempts 2
    } catch {
        Write-Host "  GitHub sync failed; continuing with the local copy." -ForegroundColor Yellow
    }
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    $pythonCommand = "py"
    $pythonArgs = @("-3")
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3.10+ was not found. Install Python, then retry." }
    $pythonCommand = "python"
    $pythonArgs = @()
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "  ✦ Preparing CryptoPulse..." -ForegroundColor Cyan
    & $pythonCommand @pythonArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create Python virtual environment." }
}

$venvPython = (Resolve-Path ".venv\Scripts\python.exe").Path
$requirementsHash = (Get-FileHash -Path "requirements.txt" -Algorithm SHA256).Hash
$stampPath = Join-Path $PSScriptRoot ".venv\requirements.sha256"
$installedHash = ""
if (Test-Path $stampPath) {
    $installedHash = (Get-Content $stampPath -Raw -ErrorAction SilentlyContinue).Trim()
}

# Skip pip completely on normal launches; reinstall only when requirements.txt changes.
if ($installedHash -ne $requirementsHash) {
    $logPath = Join-Path $env:TEMP "cryptopulse-install.log"
    $installBaseArgs = @(
        "-m", "pip", "install", "-r", "requirements.txt",
        "--retries", "3",
        "--resume-retries", "3",
        "--timeout", "60",
        "--disable-pip-version-check",
        "--no-warn-script-location",
        "--no-input",
        "-q"
    )

    # Try several China-hosted PyPI mirrors in sequence for networks where one mirror is blocked.
    $mirrors = @(
        @{ Name = "Aliyun China mirror"; Url = "https://mirrors.aliyun.com/pypi/simple/" },
        @{ Name = "Huawei Cloud China mirror"; Url = "https://repo.huaweicloud.com/repository/pypi/simple/" },
        @{ Name = "Tencent China mirror"; Url = "https://mirrors.cloud.tencent.com/pypi/simple/" },
        @{ Name = "Tsinghua China mirror"; Url = "https://pypi.tuna.tsinghua.edu.cn/simple/" }
    )

    $installed = $false
    foreach ($mirror in $mirrors) {
        $mirrorArgs = $installBaseArgs + @("--index-url", $mirror.Url)
        try {
            Invoke-QuietProcess -File $venvPython -Arguments $mirrorArgs -Message ("Installing modules (" + $mirror.Name + ")") -LogPath $logPath -MaxAttempts 1 -SuppressFailureOutput
            $installed = $true
            break
        } catch {
            Write-Host ("  Mirror failed: " + $mirror.Name + "; trying next China mirror...") -ForegroundColor Yellow
        }
    }

    if (-not $installed) {
        Write-Host "  All China mirrors failed. Check your network connection and retry." -ForegroundColor Red
        if (Test-Path $logPath) { Get-Content $logPath -Tail 10 | Write-Host }
        if (Test-Path "$logPath.err") { Get-Content "$logPath.err" -Tail 16 | Write-Host }
        throw "Could not install Python dependencies from China mirrors."
    }

    Set-Content -Path $stampPath -Value $requirementsHash -Encoding ASCII
} else {
    Write-Host "  ✦ Dependencies already ready" -ForegroundColor Green
}

# The art-based cyber splash runs after dependencies are ready and adds only a short animation.
if (Test-Path "launcher_banner.py") {
    & $venvPython "launcher_banner.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  CRYPTOPULSE // MARKET LAB" -ForegroundColor Cyan
    }
}

# Show the OS/system ASCII logo. Keep launch resilient if BasicFetch has an issue.
$basicFetchExe = Join-Path $PSScriptRoot ".venv\Scripts\basicfetch.exe"
if (Test-Path $basicFetchExe) {
    try {
        & $basicFetchExe --no-clear
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  BasicFetch logo skipped; continuing launch." -ForegroundColor DarkGray
        }
    } catch {
        Write-Host "  BasicFetch logo skipped; continuing launch." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  ✦ Launching CryptoPulse..." -ForegroundColor Magenta
& $venvPython run.py
