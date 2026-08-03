$ErrorActionPreference = "Stop"

$serverDir = Split-Path -Parent $PSScriptRoot
$desktopRepo = "https://github.com/3588044667HZ/open-note-frontend.git"
$mobileRepo = "https://github.com/3588044667HZ/open-note-mobile.git"
$buildDir = Join-Path $Env:TEMP "open-note-build"

Write-Host "[1/4] Building desktop frontend..."
$desktopBuildDir = Join-Path $buildDir "desktop"
if (Test-Path $desktopBuildDir) { Remove-Item -Recurse -Force $desktopBuildDir }
git clone $desktopRepo $desktopBuildDir --depth 1 2>$null
Push-Location $desktopBuildDir
npm install --silent 2>$null
npm run build
Pop-Location
$desktopTarget = Join-Path $serverDir "static\desktop"
if (Test-Path $desktopTarget) { Remove-Item -Recurse -Force $desktopTarget }
Copy-Item -Recurse (Join-Path $desktopBuildDir "dist") $desktopTarget

Write-Host "[2/4] Building mobile frontend..."
$mobileBuildDir = Join-Path $buildDir "mobile"
if (Test-Path $mobileBuildDir) { Remove-Item -Recurse -Force $mobileBuildDir }
git clone $mobileRepo $mobileBuildDir --depth 1 2>$null
Push-Location $mobileBuildDir
npm install --silent 2>$null
npm run build
Pop-Location
$mobileTarget = Join-Path $serverDir "static\mobile"
if (Test-Path $mobileTarget) { Remove-Item -Recurse -Force $mobileTarget }
Copy-Item -Recurse (Join-Path $mobileBuildDir "dist") $mobileTarget

Write-Host "[3/4] Building admin frontend..."
$adminDir = Join-Path $serverDir "admin-frontend"
Push-Location $adminDir
npm install --silent 2>$null
npm run build
Pop-Location

Write-Host "[4/4] Installing Python dependencies..."
Push-Location $serverDir
pip install -r requirements.txt -q
Pop-Location

Write-Host ""
Write-Host "Deploy complete. Starting server..."
python -c "from app import create_app; from waitress import serve; app=create_app(); print('Starting on http://0.0.0.0:5000'); serve(app, host='0.0.0.0', port=5000)"
