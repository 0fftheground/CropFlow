param(
    [string]$DatabaseUrl,
    [string]$FarmFieldSourceUrl,
    [ValidateSet("reference", "demo")]
    [string]$SeedMode = "reference",
    [switch]$SkipMigrate,
    [switch]$SkipSeed,
    [switch]$ReplaceFarmFieldData
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (!(Test-Path $PythonExe)) {
    throw "Project virtualenv python was not found: $PythonExe"
}

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = $env:CROPFLOW_DATABASE_URL
}

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    throw "DatabaseUrl is required. Pass -DatabaseUrl or set CROPFLOW_DATABASE_URL first."
}

$env:CROPFLOW_DATABASE_URL = $DatabaseUrl

Write-Host "Bootstrap target database via CROPFLOW_DATABASE_URL"
Write-Host "Seed mode: $SeedMode"

Push-Location $RepoRoot
try {
    if (-not $SkipMigrate) {
        Write-Host "Running alembic upgrade head..."
        & $PythonExe -m alembic -c (Join-Path $RepoRoot "alembic.ini") upgrade head
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if (-not $SkipSeed) {
        $SeedScript = if ($SeedMode -eq "demo") {
            Join-Path $RepoRoot "scripts\seed_local_dev_data.py"
        } else {
            Join-Path $RepoRoot "scripts\seed_reference_data.py"
        }

        Write-Host "Running $SeedScript ..."
        & $PythonExe $SeedScript
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($FarmFieldSourceUrl)) {
        $MigrateScript = Join-Path $RepoRoot "scripts\migrate_farm_field_data.py"
        $MigrateArgs = @(
            $MigrateScript,
            "--source-url", $FarmFieldSourceUrl,
            "--target-url", $DatabaseUrl
        )
        if ($ReplaceFarmFieldData) {
            $MigrateArgs += "--replace-target"
        }

        Write-Host "Running $MigrateScript ..."
        & $PythonExe @MigrateArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Database bootstrap completed."
