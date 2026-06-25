param(
    [string]$TargetDatabaseUrl,
    [string]$SourceDatabaseUrl,
    [ValidateSet("reference", "demo")]
    [string]$SeedMode = "reference",
    [ValidateSet("exact", "merge")]
    [string]$TableSyncMode = "merge",
    [string[]]$SyncTables,
    [switch]$PreviewTableDiff,
    [switch]$StopAfterTableDiff,
    [switch]$SkipMigrate,
    [switch]$SkipSeed,
    [switch]$SkipTableSync
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$BootstrapScript = Join-Path $RepoRoot "scripts\bootstrap-db.ps1"
$TableDiffScript = Join-Path $RepoRoot "scripts\compare_table_data.py"
$TableSyncScript = Join-Path $RepoRoot "scripts\sync_table_data.py"

if (!(Test-Path $PythonExe)) {
    throw "Project virtualenv python was not found: $PythonExe"
}

if (!(Test-Path $BootstrapScript)) {
    throw "Bootstrap script was not found: $BootstrapScript"
}

if (!(Test-Path $TableDiffScript)) {
    throw "Table diff script was not found: $TableDiffScript"
}

if (!(Test-Path $TableSyncScript)) {
    throw "Table sync script was not found: $TableSyncScript"
}

if ([string]::IsNullOrWhiteSpace($TargetDatabaseUrl)) {
    $TargetDatabaseUrl = $env:CROPFLOW_TARGET_DATABASE_URL
}

if ([string]::IsNullOrWhiteSpace($TargetDatabaseUrl)) {
    throw "TargetDatabaseUrl is required. Pass -TargetDatabaseUrl or set CROPFLOW_TARGET_DATABASE_URL first."
}

if ((-not $SkipTableSync -or $PreviewTableDiff -or $StopAfterTableDiff) -and [string]::IsNullOrWhiteSpace($SourceDatabaseUrl)) {
    Write-Host "Resolving source database URL from current local CropFlow config..."
    Push-Location $RepoRoot
    try {
        $SourceDatabaseUrl = (& $PythonExe -c "from app.core.config import get_settings; print(get_settings().get_database_url())").Trim()
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to resolve source database URL from current local config."
        }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipTableSync -or $PreviewTableDiff -or $StopAfterTableDiff) {
    if ([string]::IsNullOrWhiteSpace($SourceDatabaseUrl)) {
        throw "SourceDatabaseUrl could not be resolved. Pass -SourceDatabaseUrl explicitly or configure the local database first."
    }
    if ($SourceDatabaseUrl -eq $TargetDatabaseUrl) {
        throw "SourceDatabaseUrl and TargetDatabaseUrl must be different when configured table sync is enabled."
    }
}

$BootstrapParams = @{
    DatabaseUrl = $TargetDatabaseUrl
    SeedMode    = $SeedMode
}

if ($SkipMigrate) {
    $BootstrapParams.SkipMigrate = $true
}

if ($SkipSeed) {
    $BootstrapParams.SkipSeed = $true
}

Write-Host "Sync target database via bootstrap-db.ps1"
Write-Host "TargetDatabaseUrl: $TargetDatabaseUrl"
Write-Host "SeedMode: $SeedMode"
if (-not $SkipTableSync -or $PreviewTableDiff -or $StopAfterTableDiff) {
    Write-Host "SourceDatabaseUrl: $SourceDatabaseUrl"
    if ($SyncTables -and $SyncTables.Count -gt 0) {
        Write-Host "SyncTables: $($SyncTables -join ', ')"
    }
    else {
        Write-Host "SyncTables: default supported table set"
    }
    if (-not $SkipTableSync) {
        Write-Host "TableSyncMode: $TableSyncMode"
    }
}
else {
    Write-Host "Configured table sync skipped."
}

if ($PreviewTableDiff -or $StopAfterTableDiff) {
    $TableDiffArgs = @(
        $TableDiffScript,
        "--source-url", $SourceDatabaseUrl,
        "--target-url", $TargetDatabaseUrl
    )
    if ($SyncTables -and $SyncTables.Count -gt 0) {
        $TableDiffArgs += "--tables"
        $TableDiffArgs += $SyncTables
    }

    Write-Host "Previewing configured table diff..."
    & $PythonExe @TableDiffArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($StopAfterTableDiff) {
    Write-Host "Stopped after table diff preview."
    exit 0
}

& $BootstrapScript @BootstrapParams
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not $SkipTableSync) {
    $TableSyncArgs = @(
        $TableSyncScript,
        "--source-url", $SourceDatabaseUrl,
        "--target-url", $TargetDatabaseUrl
    )
    if ($SyncTables -and $SyncTables.Count -gt 0) {
        $TableSyncArgs += "--tables"
        $TableSyncArgs += $SyncTables
    }
    if ($TableSyncMode -eq "exact") {
        $TableSyncArgs += "--replace-target"
    }

    Write-Host "Running configured table sync..."
    & $PythonExe @TableSyncArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host "Remote database sync completed."
