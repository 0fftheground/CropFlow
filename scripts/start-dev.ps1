param(
    [ValidateSet("api", "scheduler")]
    [string]$Mode = "api",
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (!(Test-Path $PythonExe)) {
    throw "Project virtualenv python was not found: $PythonExe"
}

if ($Mode -eq "scheduler") {
    & $PythonExe -m app.jobs.runner
    exit $LASTEXITCODE
}

& $PythonExe -m uvicorn app.main:app --reload --host $Host --port $Port
