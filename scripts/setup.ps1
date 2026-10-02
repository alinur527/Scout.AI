$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path '.venv/Scripts/python.exe')) { py -3.12 -m venv .venv }
if (-not (Test-Path 'backend/.env')) {
    $privateKey = & .venv/Scripts/python.exe -c 'import secrets; print(secrets.token_urlsafe(48))'
    $example = Get-Content -LiteralPath 'backend/.env.example' -Raw
    $example.Replace('JWT_SECRET_KEY=', "JWT_SECRET_KEY=$privateKey") | Set-Content -LiteralPath 'backend/.env' -Encoding utf8
    Write-Host 'Created backend/.env with a private signing key and demo mode enabled.'
}
& .venv/Scripts/python.exe -m pip install --upgrade pip
& .venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
Push-Location frontend
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
} finally { Pop-Location }
Write-Host 'Ready. Start API, worker and frontend in three terminals; see README.'
