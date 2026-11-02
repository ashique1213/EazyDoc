# PowerShell script to generate self-signed SSL certificates for Staging
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$certsDir = Join-Path (Split-Path -Parent $scriptDir) "docker\nginx\certs"

if (-not (Test-Path $certsDir)) {
    New-Item -ItemType Directory -Path $certsDir -Force | Out-Null
}

$crtPath = Join-Path $certsDir "staging.crt"
$keyPath = Join-Path $certsDir "staging.key"

if ((Test-Path $crtPath) -and (Test-Path $keyPath)) {
    Write-Host "Staging SSL certificates already exist in $certsDir"
    exit 0
}

if (Get-Command openssl -ErrorAction SilentlyContinue) {
    Write-Host "Generating self-signed SSL certificate for staging using OpenSSL..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout $keyPath `
        -out $crtPath `
        -subj "/C=IN/ST=Karnataka/L=Bangalore/O=EazyDoc Healthcare/OU=Staging/CN=staging.eazydoc.internal"
} else {
    Write-Host "OpenSSL not found. Generating self-signed SSL certificate using Python cryptography..."
    $pyScript = Join-Path $scriptDir "generate_staging_certs.py"
    python $pyScript
}

Write-Host "Staging certificates successfully created:"
Write-Host "  Certificate: $crtPath"
Write-Host "  Private Key: $keyPath"
