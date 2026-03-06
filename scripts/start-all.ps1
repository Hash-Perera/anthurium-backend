param(
    [switch]$SkipInstall,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runDir = Join-Path $repoRoot ".local-run"
if (-not (Test-Path $runDir)) {
    New-Item -Path $runDir -ItemType Directory | Out-Null
}

function Get-PythonBootstrap {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Exe = "py"; Args = @("-3.11") }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Exe = "python"; Args = @() }
    }

    throw "Python launcher not found. Install Python 3.11 and ensure 'py' or 'python' is available in PATH."
}

$bootstrap = Get-PythonBootstrap

$services = @(
    @{
        Name = "weather"
        Path = Join-Path $repoRoot "weather"
        App = "app.main:app"
        Port = 8000
        Requirements = Join-Path $repoRoot "weather\requirements.txt"
    },
    @{
        Name = "soil"
        Path = Join-Path $repoRoot "soil"
        App = "app.main:app"
        Port = 8001
        Requirements = Join-Path $repoRoot "soil\requirements.txt"
    },
    @{
        Name = "disease"
        Path = Join-Path $repoRoot "disease"
        App = "main:app"
        Port = 8002
        Requirements = Join-Path $repoRoot "disease\requirements.txt"
    },
    @{
        Name = "price"
        Path = Join-Path $repoRoot "price"
        App = "main:app"
        Port = 8003
        Requirements = Join-Path $repoRoot "price\requirements.txt"
    }
)

$pidState = @()

foreach ($svc in $services) {
    $venvPath = Join-Path $svc.Path ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "[setup] Creating venv for $($svc.Name)..."
        & $bootstrap.Exe @($bootstrap.Args + @("-m", "venv", $venvPath))
    }

    if (-not $SkipInstall) {
        Write-Host "[setup] Installing dependencies for $($svc.Name)..."
        & $venvPython -m pip install --upgrade pip setuptools wheel
        & $venvPython -m pip install --retries 20 --timeout 1200 -r $svc.Requirements
    }

    $stdoutLog = Join-Path $runDir "$($svc.Name).out.log"
    $stderrLog = Join-Path $runDir "$($svc.Name).err.log"

    $uvicornArgs = @("-m", "uvicorn", $svc.App, "--host", "0.0.0.0", "--port", [string]$svc.Port)
    if ($Reload) {
        $uvicornArgs += "--reload"
    }

    Write-Host "[run] Starting $($svc.Name) on port $($svc.Port)..."
    $proc = Start-Process -FilePath $venvPython -ArgumentList $uvicornArgs -WorkingDirectory $svc.Path -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

    $pidState += [PSCustomObject]@{
        name = $svc.Name
        pid = $proc.Id
        port = $svc.Port
    }
}

$pidFile = Join-Path $runDir "pids.json"
$pidState | ConvertTo-Json | Set-Content -Path $pidFile

Write-Host ""
Write-Host "All services started."
Write-Host "weather: http://localhost:8000"
Write-Host "soil:    http://localhost:8001"
Write-Host "disease: http://localhost:8002"
Write-Host "price:   http://localhost:8003"
Write-Host ""
Write-Host "Logs: $runDir"
Write-Host "PIDs: $pidFile"
Write-Host "Use '.\\scripts\\stop-all.ps1' to stop all services."
