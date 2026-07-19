# Start IoT & AI Platform
Set-Location $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   IoT & AI Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install Python 3.11+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
python -m pip install -q -r requirements.txt 2>&1 | Out-Null

Write-Host "Starting Python server (Tuya bridge built-in)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Dashboard: http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

$chromePaths = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
$chromePath = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($chromePath) { Start-Process $chromePath "http://localhost:8000" } else { Start-Process "http://localhost:8000" }
python server_final.py

Read-Host "Server exited. Press Enter to close"
