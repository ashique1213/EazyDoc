# ==============================================================================
# EazyDoc PostgreSQL Windows PowerShell Restore Utility
# ==============================================================================
param (
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$TargetDb = "eazydoc_staging_db",
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbUser = "eazydoc_user",
    [string]$DbPassword = $env:DATABASE_PASSWORD
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    Write-Error "Backup file '$BackupFile' does not exist."
}

$checksumFile = "${BackupFile}.sha256"
if (Test-Path $checksumFile) {
    Write-Host "Verifying SHA-256 hash..."
    $expected = (Get-Content $checksumFile).Trim().ToLower()
    $actual = (Get-FileHash -Path $BackupFile -Algorithm SHA256).Hash.ToLower()
    if ($expected -ne $actual) {
        Write-Error "Checksum mismatch! Expected $expected but computed $actual."
    }
    Write-Host "Integrity verification passed: SHA-256 matches."
}

Write-Host "Restoring into target database '$TargetDb'..."
$env:PGPASSWORD = $DbPassword
& "C:\Program Files\PostgreSQL\16\bin\pg_restore.exe" -h $DbHost -p $DbPort -U $DbUser -d $TargetDb --clean --if-exists --no-owner --no-acl $BackupFile

Write-Host "Restoration finished. Running verification query..."
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h $DbHost -p $DbPort -U $DbUser -d $TargetDb -c "SELECT 'accounts_user' AS tbl, count(*) FROM accounts_user UNION ALL SELECT 'clinics_clinic', count(*) FROM clinics_clinic UNION ALL SELECT 'appointments_appointment', count(*) FROM appointments_appointment;"

