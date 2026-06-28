# build.ps1 — Compile MBM Mod Loader into a single portable .exe
#
# Usage:
#   .\build.ps1
#   .\build.ps1 -PythonExe "python3"   # specify a different Python executable

param(
    [string]$PythonExe = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$DistDir     = Join-Path $ProjectRoot "dist"
$BuildDir    = Join-Path $ProjectRoot "build"
$SpecFile    = Join-Path $ProjectRoot "MBM_ModLoader.spec"
$OutputExe   = Join-Path $DistDir "MBM_ModLoader.exe"

function Write-Step([string]$msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

# ── 1. Verify Python ──────────────────────────────────────────────────────────
Write-Step "Checking Python"
try {
    $pyVer = & $PythonExe --version 2>&1
    Write-Host "    $pyVer" -ForegroundColor Green
} catch {
    Write-Host "ERROR: '$PythonExe' not found. Install Python 3.x and add it to PATH." -ForegroundColor Red
    exit 1
}

# ── 2. Install / upgrade PyInstaller ─────────────────────────────────────────
Write-Step "Installing / upgrading PyInstaller"
& $PythonExe -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install pyinstaller failed." -ForegroundColor Red
    exit 1
}

# ── 3. Clean previous artifacts ───────────────────────────────────────────────
Write-Step "Cleaning previous build artifacts"
foreach ($path in @($DistDir, $BuildDir, $SpecFile)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
        Write-Host "    Removed: $path"
    }
}

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
Write-Step "Running PyInstaller"
Push-Location $ProjectRoot
try {
    & $PythonExe -m PyInstaller `
        --onefile `
        --noconsole `
        --name "MBM_ModLoader" `
        --paths "src" `
        --add-data "assets;assets" `
        --add-data "language;language" `
        --add-data "data;data" `
        main.py

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: PyInstaller exited with code $LASTEXITCODE." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

# ── 5. Remove intermediate artifacts (keep dist\ only) ───────────────────────
Write-Step "Cleaning intermediate artifacts"
foreach ($path in @($BuildDir, $SpecFile)) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force
        Write-Host "    Removed: $path"
    }
}

# ── 6. Done ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Output: $OutputExe" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Green
