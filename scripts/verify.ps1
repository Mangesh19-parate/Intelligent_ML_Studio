# Intelligent ML Studio - Windows PowerShell Verification Wrapper
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting Intelligent ML Studio Verification Runner" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

python "$RootDir\scripts\verify.py" @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
