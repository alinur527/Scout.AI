$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Project Python environment is missing.' }
& $pythonExe (Join-Path $PSScriptRoot 'local_runtime.py') stop
if ($LASTEXITCODE -ne 0) { throw 'Some recorded processes could not be verified/stopped; no unrelated process was stopped.' }
