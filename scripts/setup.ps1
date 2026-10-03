$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install Python 3.12 with the Windows py launcher first.' }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node 22.12+ first.' }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm is required.' }
    & py -3.12 -c 'import sys; assert sys.version_info[:2] == (3, 12)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
    $nodeVersion = & node --version
    if ($LASTEXITCODE -ne 0 -or [version]$nodeVersion.TrimStart('v') -lt [version]'22.12') { throw 'Node 22.12+ is required; CI uses Node 22.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    & .venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    & .venv/Scripts/python.exe scripts/configure_local.py
    if ($LASTEXITCODE -ne 0) { throw 'Local configuration failed; existing configuration was preserved.' }
    Push-Location frontend
    try {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
    Push-Location backend
    try {
        & ../.venv/Scripts/python.exe -m app.db.migrate
        if ($LASTEXITCODE -ne 0) { throw 'Migration failed. Do not delete your database; check the operations guide.' }
    } finally { Pop-Location }
    & .venv/Scripts/python.exe scripts/local_runtime.py doctor
    if ($LASTEXITCODE -ne 0) { throw 'Doctor found a configuration problem.' }
    Write-Host 'Setup complete. Run .\scripts\start.ps1. Existing .env and data preserved; no CV weights downloaded.'
} finally { Pop-Location }
