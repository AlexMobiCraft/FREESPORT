# Test B2B User Registration (Second attempt)

$body = @{
    email = "test-trainer2@example.com"
    password = "TestPass123!"
    password_confirm = "TestPass123!"
    first_name = "Petr"
    last_name = "Ivanov"
    role = "trainer"
    company_name = "Fitness Club Pro"
    tax_id = "9876543210"
} | ConvertTo-Json

Write-Host "Sending B2B registration request (attempt 2)..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register/" -Method Post -Body $body -ContentType "application/json"
    
    Write-Host ""
    Write-Host "SUCCESS! Registration completed." -ForegroundColor Green
    Write-Host "Server response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 3
    
    Write-Host ""
    Write-Host "Now checking Celery logs for email tasks..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    
} catch {
    Write-Host ""
    Write-Host "ERROR during registration:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details:" -ForegroundColor Yellow
        $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 3
    }
}
