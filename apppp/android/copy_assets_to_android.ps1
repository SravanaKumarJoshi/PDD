# copy_assets_to_android.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Copies generated ML assets from PolysaccharideProject/app_assets/
# into the Android app module app/src/main/assets/
#
# Run from: D:\Sravan\PDD\apppp\android\
# Usage: powershell -ExecutionPolicy Bypass -File .\copy_assets_to_android.ps1
# ─────────────────────────────────────────────────────────────────────────────

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot      = $PSScriptRoot
$AssetSrc      = Join-Path $RepoRoot "PolysaccharideProject\app_assets"
$AndroidAssets = Join-Path $RepoRoot "app\src\main\assets"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Polysaccharide Project - Copy Assets to Android" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ("  Source : {0}" -f $AssetSrc)
Write-Host ("  Dest   : {0}" -f $AndroidAssets)
Write-Host ""

if (-not (Test-Path $AssetSrc)) {
  Write-Host ("ERROR: Source folder not found: {0}" -f $AssetSrc) -ForegroundColor Red
  exit 1
}

New-Item -ItemType Directory -Force -Path $AndroidAssets | Out-Null

# Required files for the app
$files = @(
  "trained_model.tflite",
  "model_manifest.json",
  "feature_columns.json",
  "label_classes.json",
  "android_preprocessing.json",
  "master_dataset.json",
  "polysaccharide_knowledge_base.json"
)

$copied = 0
$missing = @()

foreach ($file in $files) {
  $src = Join-Path $AssetSrc $file
  $dst = Join-Path $AndroidAssets $file

  if (Test-Path $src) {
    Copy-Item -Path $src -Destination $dst -Force
    $sizeMb = [math]::Round((Get-Item $src).Length / 1MB, 3)
    Write-Host ("  [OK] Copied {0} ({1} MB)" -f $file, $sizeMb) -ForegroundColor Green
    $copied++
  } else {
    $missing += $file
    Write-Host ("  [MISSING] {0}" -f $src) -ForegroundColor Red
  }
}

Write-Host ""
Write-Host ("Done. {0}/{1} files copied to Android assets." -f $copied, $files.Count) -ForegroundColor Cyan

if ($missing.Count -gt 0) {
  Write-Host ("FAILED: Missing required files: {0}" -f ($missing -join ", ")) -ForegroundColor Red
  exit 1
}

Write-Host "SUCCESS: All required files are present." -ForegroundColor Green
Write-Host ""
