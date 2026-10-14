<#
.SYNOPSIS
    xbot installer for Windows PowerShell
.DESCRIPTION
    Downloads and installs the standalone xbot executable, configuring User PATH.
.EXAMPLE
    irm https://raw.githubusercontent.com/atpaawej/xbot/main/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [string]$Version = "latest",
    [string]$InstallDir = "$HOME\.xbot\bin"
)

$ErrorActionPreference = "Stop"

$Repo = "atpaawej/xbot"

function Write-Info {
    param([string]$Message)
    Write-Host "==> " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "==> " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "Warning: " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "Error: " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
    exit 1
}

# Header Banner
Write-Host ""
Write-Host "    __  __ ___   ____  ____  ______" -ForegroundColor Cyan
Write-Host "    \ \/ // _ ) / __ \/_  / /_  __/" -ForegroundColor Cyan
Write-Host "     \  // _  |/ /_/ / / /_  / /   " -ForegroundColor Cyan
Write-Host "     /_//____/ \____/ /___/ /_/    " -ForegroundColor Cyan
Write-Host ""
Write-Host "Autonomous AI Agent with Rich TUI & Web Intelligence" -ForegroundColor Gray
Write-Host "----------------------------------------------------" -ForegroundColor Gray
Write-Host ""

# 1. Architecture Check
if (-not [System.Environment]::Is64BitOperatingSystem) {
    Write-Err "xbot currently requires a 64-bit Windows operating system."
}

$Asset = "xbot-windows-x86_64.exe"
Write-Info "Target binary: $Asset"

# 2. Ensure Install Directory Exists
if (-not (Test-Path -Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$TargetExe = Join-Path $InstallDir "xbot.exe"
$TempExe = Join-Path $env:TEMP "xbot-$([Guid]::NewGuid()).exe"

# 3. Determine Download URL
if ($Version -eq "latest") {
    $DownloadUrl = "https://github.com/$Repo/releases/latest/download/$Asset"
} else {
    $DownloadUrl = "https://github.com/$Repo/releases/download/$Version/$Asset"
}

Write-Info "Downloading from $DownloadUrl..."
$Downloaded = $false

try {
    # Prefer curl.exe if available (faster and handles large streaming downloads reliably)
    if (Get-Command "curl.exe" -ErrorAction SilentlyContinue) {
        & curl.exe -fsSL "$DownloadUrl" -o "$TempExe"
        if ($LASTEXITCODE -eq 0 -and (Test-Path $TempExe)) {
            $Downloaded = $true
        }
    }

    if (-not $Downloaded) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $TempExe -UseBasicParsing
        if (Test-Path $TempExe) {
            $Downloaded = $true
        }
    }
} catch {
    Write-Warn "Direct release download failed: $_"
}

# 4. Fallback to uv tool or pipx if direct binary download fails
if (-not $Downloaded -or (Get-Item $TempExe).Length -lt 1000) {
    Remove-Item -Path $TempExe -Force -ErrorAction SilentlyContinue

    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        Write-Info "Attempting fallback installation via uv tool..."
        & uv tool install --force "git+https://github.com/$Repo.git"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "xbot installed successfully via uv tool!"
            exit 0
        }
    } elseif (Get-Command "pipx" -ErrorAction SilentlyContinue) {
        Write-Info "Attempting fallback installation via pipx..."
        & pipx install --force "git+https://github.com/$Repo.git"
        if ($LASTEXITCODE -eq 0) {
            Write-Success "xbot installed successfully via pipx!"
            exit 0
        }
    }

    Write-Err "Could not download $Asset and no uv/pipx fallback was found."
}

# Move downloaded binary to target
Move-Item -Path $TempExe -Destination $TargetExe -Force
Write-Success "Installed executable to $TargetExe"

# 5. Add to User PATH if not present
$UserPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
$PathEntries = $UserPath -split ";" | ForEach-Object { $_.TrimEnd("\") }

if ($PathEntries -notcontains $InstallDir.TrimEnd("\")) {
    Write-Info "Adding $InstallDir to User PATH environment variable..."
    $NewPath = if ([string]::IsNullOrWhiteSpace($UserPath)) { $InstallDir } else { "$UserPath;$InstallDir" }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, [EnvironmentVariableTarget]::User)
    $env:Path = "$InstallDir;$env:Path"
    Write-Success "PATH updated successfully."
} else {
    $env:Path = "$InstallDir;$env:Path"
}

# 6. Verification
Write-Host ""
Write-Success "Installation Complete!"
try {
    & "$TargetExe" --version
} catch {
    Write-Host "Run 'xbot --version' in a new PowerShell window." -ForegroundColor Cyan
}

Write-Host "Start an interactive session with: xbot" -ForegroundColor Cyan
