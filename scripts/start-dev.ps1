param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

python -m uvicorn app.main:app --reload --host $Host --port $Port
