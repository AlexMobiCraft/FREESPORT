# Test B2B User Registration (Fourth attempt with new Gmail account)

$body = @{
    email = "test-trainer4@example.com"
    password = "TestPass123!"
    password_confirm = "TestPass123!"
    first_name = "Sergey"
    last_name = "Volkov"
    role = "trainer"
    company_name = "CrossFit Box Elite"
    tax_id = "7777777777"
} | ConvertTo-Json

Write-Host "Sending B2B registration request (attempt 4 - new Gmail)..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/auth/register/" -Method Post -Body $body -ContentType "application/json"
    
    Write-Host ""
    Write-Host "SUCCESS! Registration completed." -ForegroundColor Green
    Write-Host "User ID: $($response.user.id)" -ForegroundColor Yellow
    Write-Host "Email: $($response.user.email)" -ForegroundColor Yellow
    Write-Host "Role: $($response.user.role)" -ForegroundColor Yellow
    
    Write-Host ""
    Write-Host "Waiting 5 seconds for Celery to process email tasks..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "Check your Gmail inbox (alexmw2006@gmail.com) for admin notification!" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "ERROR during registration:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
