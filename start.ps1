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
    $frames = @('|','/','-','\')

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
            Write-Host ("  [OK] {0}   " -f $Message) -ForegroundColor Green
            return
        }

        if ($attempt -lt $MaxAttempts) {
            Write-Host ("  [RETRY] Retrying {0}..." -f $Message) -ForegroundColor Yellow
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
Write-Host "  +------------------------------------------+" -ForegroundColor Green
Write-Host "  |        CRYPTOPULSE // MARKET LAB         |" -ForegroundColor Green
Write-Host "  +------------------------------------------+" -ForegroundColor Green
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

# Hosted mode: "panel" starts a fresh GitHub Actions dashboard run instead of the local server.
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
    Write-Host "  [BOOT] Preparing CryptoPulse..." -ForegroundColor Green
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
        @{ Name = "Liara Iran PyPI mirror"; Url = "https://package-mirror.liara.ir/repository/pypi/simple/" },
        @{ Name = "Aliyun China mirror"; Url = "https://mirrors.aliyun.com/pypi/simple/" },
        @{ Name = "Huawei Cloud China mirror"; Url = "https://repo.huaweicloud.com/repository/pypi/simple/" },
        @{ Name = "Tencent China mirror"; Url = "https://mirrors.cloud.tencent.com/pypi/simple/" },
        @{ Name = "SUSTech China mirror"; Url = "https://mirrors.sustech.edu.cn/pypi/web/simple/" },
        @{ Name = "Tsinghua China mirror"; Url = "https://pypi.tuna.tsinghua.edu.cn/simple/" },
        @{ Name = "Tsinghua alternate endpoint"; Url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/" }
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
        # Automatically diagnose HTTPS access and make one detailed Aliyun attempt.
        # This avoids asking the user to run separate troubleshooting commands.
        Write-Host "  China mirrors failed; checking HTTPS and collecting pip diagnostics..." -ForegroundColor Yellow

        foreach ($url in @(
            "https://package-mirror.liara.ir/repository/pypi/simple/flask/",
            "https://mirrors.aliyun.com/pypi/simple/flask/",
            "https://pypi.tuna.tsinghua.edu.cn/simple/flask/",
            "https://repo.huaweicloud.com/repository/pypi/flask/"
        )) {
            try {
                $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
                Write-Host ("  HTTPS OK ({0}): HTTP {1}" -f ([uri]$url).Host, [int]$response.StatusCode) -ForegroundColor Green
            } catch {
                Write-Host ("  HTTPS failed ({0}): {1}" -f ([uri]$url).Host, $_.Exception.Message) -ForegroundColor Yellow
            }
        }

        $diagnosticLog = Join-Path $env:TEMP "cryptopulse-pip-diagnostic.log"
        $diagnosticErr = "$diagnosticLog.err"
        Remove-Item $diagnosticLog, $diagnosticErr -Force -ErrorAction SilentlyContinue
        $diagnosticArgs = @(
            "-m", "pip", "install", "-r", "requirements.txt",
            "--index-url", "https://mirrors.aliyun.com/pypi/simple/",
            "--timeout", "20",
            "--retries", "0",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--no-input",
            "-vv"
        )
        try {
            Invoke-QuietProcess -File $venvPython -Arguments $diagnosticArgs -Message "Detailed dependency retry (Liara)" -LogPath $diagnosticLog -MaxAttempts 1 -SuppressFailureOutput
            $installed = $true
        } catch {
            Write-Host "  Automatic diagnostic retry reported a failure. Last pip messages:" -ForegroundColor Yellow
            if (Test-Path $diagnosticLog) { Get-Content $diagnosticLog -Tail 25 | Write-Host }
            if (Test-Path $diagnosticErr) { Get-Content $diagnosticErr -Tail 25 | Write-Host }

            # Start-Process can report a misleading failure on some Windows/PowerShell setups.
            # If the direct dependencies are already installed and pip reports no broken
            # dependencies, don't block panel startup just because the retry exit code failed.
            try {
                & $venvPython -m pip check
                $pipCheckExit = $LASTEXITCODE
                if ($pipCheckExit -eq 0) {
                    $requiredPackages = @("Flask", "requests", "art", "basicfetch")
                    $packagesPresent = $true
                    foreach ($packageName in $requiredPackages) {
                        & $venvPython -m pip show $packageName *> $null
                        if ($LASTEXITCODE -ne 0) {
                            $packagesPresent = $false
                            break
                        }
                    }
                    if ($packagesPresent) {
                        Write-Host "  Dependencies are already installed and pip check passed; continuing." -ForegroundColor Green
                        $installed = $true
                    }
                }
            } catch { }
        }
    }

    if (-not $installed) {
        throw "Dependency installation failed. The HTTPS and detailed pip errors are shown above."
    }

    Set-Content -Path $stampPath -Value $requirementsHash -Encoding ASCII
} else {
    Write-Host "  [OK] Dependencies already ready" -ForegroundColor Green
}

# The art-based cyber splash runs after dependencies are ready and adds only a short animation.
if (Test-Path "launcher_banner.py") {
    & $venvPython "launcher_banner.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  CRYPTOPULSE // MARKET LAB" -ForegroundColor Cyan
    }
}

Write-Host "  [START] Launching CryptoPulse..." -ForegroundColor Green
& $venvPython run.py
