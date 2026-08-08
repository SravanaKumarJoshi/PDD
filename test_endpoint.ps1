$ErrorActionPreference = "Stop"
Start-Sleep -Seconds 2

Write-Host "`n=== Health check ===" -ForegroundColor Cyan
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 10
    Write-Host "Health status: $($health.StatusCode)"
    Write-Host $health.Content
} catch {
    Write-Host "Health check failed: $_" -ForegroundColor Red
}

Write-Host "`n=== GET /api/v1/materials?page=1&page_size=5 ===" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/materials?page=1&page_size=5" -UseBasicParsing -TimeoutSec 30
    Write-Host "HTTP Status : $($resp.StatusCode)"
    # Pretty-print first 800 chars of JSON
    $json = $resp.Content | ConvertFrom-Json -Depth 5
    Write-Host "total       : $($json.total)"
    Write-Host "page        : $($json.page)"
    Write-Host "page_size   : $($json.page_size)"
    Write-Host "items count : $($json.items.Count)"
    if ($json.items.Count -gt 0) {
        $first = $json.items[0]
        Write-Host "First item id   : $($first.id)"
        Write-Host "First item name : $($first.name)"
        Write-Host "First item cat  : $($first.category)"
    }
    Write-Host "`nENDPOINT OK - returned data successfully" -ForegroundColor Green
} catch {
    Write-Host "Request failed: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        Write-Host $reader.ReadToEnd()
    }
}

Write-Host "`n=== GET /api/v1/materials/sync (delta sync) ===" -ForegroundColor Cyan
try {
    $sync = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/materials/sync" -UseBasicParsing -TimeoutSec 30
    Write-Host "HTTP Status : $($sync.StatusCode)"
    $syncJson = $sync.Content | ConvertFrom-Json -Depth 3
    Write-Host "Sync items  : $($syncJson.items.Count)"
    Write-Host "Has more    : $($syncJson.has_more)"
    Write-Host "SYNC ENDPOINT OK" -ForegroundColor Green
} catch {
    Write-Host "Sync request: $_" -ForegroundColor Yellow
}
