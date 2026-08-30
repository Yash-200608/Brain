# Stop duplicate Chimera stack processes on PC (Brain API + PC node).
# Usage: .\scripts\stop_chimera_stack.ps1

$BrainRoot = Split-Path -Parent $PSScriptRoot
$BrainVenvMarker = Join-Path $BrainRoot "venv\Scripts\python.exe"

Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {
    $cmd = $_.CommandLine
    ($cmd -match 'main\.py api' -or $cmd -match 'run_chimera_node\.py')
} | ForEach-Object {
    Write-Host "Stopping PID $($_.ProcessId): $($_.CommandLine.Substring(0, [Math]::Min(90, $_.CommandLine.Length)))"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host "Done. Mosquitto and dashboard are left running."
