$ErrorActionPreference = "Stop"

$serverDir = Split-Path -Parent $PSScriptRoot
$desktopDist = "E:\WebStormProjects\open-note-frontend\dist"
$mobileDist = "E:\WebStormProjects\open-note-mobile\dist"

Write-Host "[1/4] Building desktop frontend..."
Push-Location "E:\WebStormProjects\open-note-frontend"
npm run build
Pop-Location

Write-Host "[2/4] Building mobile frontend..."
Push-Location "E:\WebStormProjects\open-note-mobile"
npm run build
Pop-Location

Write-Host "[3/4] Copying static files..."
$desktopTarget = Join-Path $serverDir "static\desktop"
$mobileTarget = Join-Path $serverDir "static\mobile"

if (Test-Path $desktopTarget) { Remove-Item -Recurse -Force $desktopTarget }
if (Test-Path $mobileTarget) { Remove-Item -Recurse -Force $mobileTarget }

Copy-Item -Recurse $desktopDist $desktopTarget
Copy-Item -Recurse $mobileDist $mobileTarget

Write-Host "[4/4] Installing Python dependencies..."
Push-Location $serverDir
& "$serverDir\.venv\Scripts\python.exe" -m pip install -r requirements.txt -q

Write-Host ""
Write-Host "Deploy complete. Starting server..."
& "$serverDir\.venv\Scripts\python.exe" -c "from app import create_app; from waitress import serve; app=create_app(); print('Starting on http://0.0.0.0:5000'); serve(app, host='0.0.0.0', port=5000)"
