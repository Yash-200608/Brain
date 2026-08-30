# Start Chimera stack (Mosquitto check + Brain API + PC node + dashboard).
# Phone node: start separately on Termux via run_chimera_proot.sh.
#
# Usage: .\scripts\start_chimera_stack.ps1
# Prerequisites: Mosquitto on Tailscale IP, Brain .env, C:\chimera\node-pc.env

$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent $PSScriptRoot
$JarvisRoot = Join-Path (Split-Path -Parent $BrainRoot) "JARVIS"
$PcEnv = "C:\chimera\node-pc.env"
$BrainVenv = Join-Path $BrainRoot "venv\Scripts\python.exe"
$Mosquitto = "C:\Program Files\mosquitto\mosquitto.exe"
$MosquittoConf = "C:\Program Files\mosquitto\mosquitto.conf"

function Test-PortListening($port) {
    return [bool](netstat -ano | Select-String ":$port\s" | Select-String "LISTENING")
}

function Stop-DuplicateChimeraProcesses {
    $existing = Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {
        $_.CommandLine -match 'main\.py api' -or $_.CommandLine -match 'run_chimera_node\.py'
    }
    if ($existing) {
        Write-Host "Stopping existing Brain/node processes (prevent duplicate MQTT clients)"
        $existing | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 2
    }
}

Stop-DuplicateChimeraProcesses

if (-not (Test-PortListening 1883)) {
    if (Test-Path $Mosquitto) {
        Write-Host "Starting Mosquitto on :1883"
        Start-Process -FilePath $Mosquitto -ArgumentList "-c", $MosquittoConf -WindowStyle Minimized
        Start-Sleep -Seconds 2
    } else {
        Write-Warning "Mosquitto not listening on :1883 — start the broker first"
    }
}

if (-not (Test-Path $BrainVenv)) {
    Write-Warning "Brain venv not found at $BrainVenv — using system python"
    $BrainVenv = "python"
}

Write-Host "Starting Brain API on :8000 (python main.py api)"
Start-Process -FilePath $BrainVenv -ArgumentList "main.py", "api" `
    -WorkingDirectory $BrainRoot -WindowStyle Minimized
Start-Sleep -Seconds 4

if (-not (Test-PortListening 5173)) {
    Write-Host "Starting dashboard on http://localhost:5173"
    Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "5173" `
        -WorkingDirectory (Join-Path $BrainRoot "frontend\dashboard") -WindowStyle Minimized
} else {
    Write-Host "Dashboard already listening on :5173"
}

if (Test-Path $PcEnv) {
    $nodeScript = Join-Path $JarvisRoot "run_chimera_node.py"
    if (Test-Path $nodeScript) {
        Write-Host "Starting PC chimera node ($PcEnv)"
        Start-Process -FilePath $BrainVenv -ArgumentList $nodeScript, "--env-file", $PcEnv `
            -WorkingDirectory $JarvisRoot -WindowStyle Minimized
    } else {
        Write-Warning "run_chimera_node.py not found at $nodeScript"
    }
} else {
    Write-Warning "PC node env missing: $PcEnv — run provisioning or create from Brain/.env"
}

Write-Host ""
Write-Host "Open dashboard: http://localhost:5173"
Write-Host "Trial report:   GET http://localhost:8000/api/devices/trial-report"
Write-Host "Phone node:     ssh to Termux, run ~/Jarvis-2.0/scripts/run_chimera_proot.sh"
