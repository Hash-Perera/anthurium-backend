$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pidFile = Join-Path $repoRoot ".local-run\pids.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "No PID state file found at $pidFile"
    exit 0
}

$entries = Get-Content $pidFile -Raw | ConvertFrom-Json

foreach ($entry in $entries) {
    try {
        $proc = Get-Process -Id $entry.pid -ErrorAction Stop
        Stop-Process -Id $entry.pid -Force
        Write-Host "Stopped $($entry.name) (PID $($entry.pid), port $($entry.port))"
    }
    catch {
        Write-Host "Process for $($entry.name) not running (PID $($entry.pid))"
    }
}

Remove-Item $pidFile -Force
Write-Host "All tracked services are stopped."
