$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run scripts/setup.ps1 first.' }
& $pythonExe (Join-Path $PSScriptRoot 'local_runtime.py') doctor
if ($LASTEXITCODE -ne 0) { throw 'Doctor found a problem; see the diagnostic above.' }
