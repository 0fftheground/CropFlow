param(
    [ValidateSet("api", "scheduler")]
    [string]$Mode = "api",
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

if ($Mode -eq "scheduler") {
    python -m app.jobs.runner
    exit $LASTEXITCODE
}

python -m uvicorn app.main:app --reload --host $Host --port $Port
