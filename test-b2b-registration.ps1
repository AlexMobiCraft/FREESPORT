# Test B2B User Registration

$body = @{
    email = "test-trainer@example.com"
    password = "TestPass123!"
    password_confirm = "TestPass123!"
    first_name = "Ivan"
    last_name = "Testov"
    role = "trainer"
    company_name = "Sport Club Champion"
    tax_id = "1234567890"
} | ConvertTo-Json

Write-Host "Sending B2B registration request..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register/" -Method Post -Body $body -ContentType "application/json"
    
    Write-Host ""
    Write-Host "SUCCESS! Registration completed." -ForegroundColor Green
    Write-Host "Server response:" -ForegroundColor Yellow
    $response | ConvertTo-Json -Depth 3
    
    Write-Host ""
    Write-Host "Check emails:" -ForegroundColor Cyan
    Write-Host "  - alex.mobicraft@gmail.com (admin notification)" -ForegroundColor White
    Write-Host "  - test-trainer@example.com (user confirmation)" -ForegroundColor White
    
} catch {
    Write-Host ""
    Write-Host "ERROR during registration:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details:" -ForegroundColor Yellow
        $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 3
    }
}
