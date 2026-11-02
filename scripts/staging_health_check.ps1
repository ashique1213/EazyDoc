# PowerShell script for Staging Health Check
param(
    [string]$BaseUrl = "http://localhost"
)

$healthUrl = "$($BaseUrl.TrimEnd('/'))/api/v1/health/"
Write-Host "=== EazyDoc Staging Operational Health Check ==="
Write-Host "Target Health Endpoint: $healthUrl"

try {
    $response = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5 -Headers @{ "User-Agent" = "EazyDoc-Staging-HealthCheck/1.0" }
    Write-Host "Service Status: $($response.status)"
    Write-Host "Database: $($response.database)"
    Write-Host "Redis Cache: $($response.redis)"

    if ($response.status -eq "ok" -and $response.database -eq "ok") {
        Write-Host "`n[SUCCESS] Staging core application and backing stores are fully operational." -ForegroundColor Green
        exit 0
    } else {
        Write-Host "`n[WARNING] Staging service reported degraded health." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "`n[ERROR] Health check request failed: $_" -ForegroundColor Red
    Write-Host "Ensure staging containers (Nginx, Daphne/backend, Postgres, Redis) are running."
    exit 2
}

