# ICT Trader • Autonomous Multi-Market 24/5 Launcher
# Starts MetaTrader 5 (if not already running) and initiates the autonomous multi-market portfolio scanner.
#
# Usage:
#   .\start_autonomous.ps1            (Runs in Paper Trading / Dry Run mode - Safe monitoring)
#   .\start_autonomous.ps1 -Execute   (Runs in LIVE execution mode - executes real trades on MT5)

param (
    [switch]$Execute,
    [switch]$RealAccount
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   ◈ ICT ALGORITHMIC TRADING SYSTEM • SAAS PRO DAEMON    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure MetaTrader 5 is running
$mt5Process = Get-Process -Name "terminal64" -ErrorAction SilentlyContinue
if (-not $mt5Process) {
    Write-Host "[1/3] Launching MetaTrader 5 terminal..." -ForegroundColor Yellow
    $mt5Path = "C:\Program Files\MetaTrader 5\terminal64.exe"
    if (Test-Path $mt5Path) {
        Start-Process $mt5Path
        Start-Sleep -Seconds 5
    } else {
        Write-Host "WARNING: MT5 terminal not found at $mt5Path. Please ensure MT5 is open." -ForegroundColor Red
    }
} else {
    Write-Host "[1/3] MetaTrader 5 is active (PID: $($mt5Process.Id))" -ForegroundColor Green
}

# 2. Set environment path for Python and uv
$env:Path = "C:\Users\giant\.local\bin;$env:Path"

# 3. Determine Execution Mode
$extraArgs = @()
if ($Execute) {
    Write-Host "[2/3] MODE: AUTOMATED BROKER EXECUTION (Active Orders Enabled)" -ForegroundColor Green
    $extraArgs += "--execute"
} else {
    Write-Host "[2/3] MODE: DRY-RUN / PAPER TRADING (Safe live feed monitoring)" -ForegroundColor Yellow
}

if ($RealAccount) {
    $extraArgs += "--allow-real-account"
}

Write-Host "[3/3] Initiating Multi-Market Scanner across Forex, Gold, and Indices..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C at any time to stop, or create a 'STOP' file for emergency kill-switch.`n" -ForegroundColor DarkGray

# Launch Portfolio Engine
uv run --with MetaTrader5 --with tzdata python -m ict_trader --config examples/portfolio.toml portfolio --news examples/calendar.example.csv @extraArgs
