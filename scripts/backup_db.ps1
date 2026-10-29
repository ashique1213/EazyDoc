# ==============================================================================
# EazyDoc PostgreSQL Windows PowerShell Backup Utility
# ==============================================================================
param (
    [string]$BackupDir = "backups",
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbName = "eazydoc_db",
    [string]$DbUser = "eazydoc_user",
    [string]$DbPassword = $env:DATABASE_PASSWORD
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $BackupDir "${DbName}_${timestamp}.dump"
$checksumFile = "${backupFile}.sha256"

Write-Host "[$([DateTime]::UtcNow.ToString('s'))Z] Starting backup for '$DbName'..."

$env:PGPASSWORD = $DbPassword
& "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -h $DbHost -p $DbPort -U $DbUser -d $DbName -F c -Z 9 -b -f $backupFile

if ($LASTEXITCODE -eq 0 -and (Test-Path $backupFile)) {
    $hash = (Get-FileHash -Path $backupFile -Algorithm SHA256).Hash.ToLower()
    $hash | Out-File -FilePath $checksumFile -Encoding utf8NoBOM
    $size = (Get-Item $backupFile).Length / 1MB
    Write-Host "[$([DateTime]::UtcNow.ToString('s'))Z] Backup succeeded: $backupFile ($([Math]::Round($size, 2)) MB)"
    Write-Host "SHA-256: $hash"
} else {
    Write-Error "Database backup failed with exit code $LASTEXITCODE."
}

