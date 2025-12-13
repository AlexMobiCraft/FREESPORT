# Test B2B User Registration (Third attempt with fixed env vars)

$body = @{
    email = "test-trainer3@example.com"
    password = "TestPass123!"
    password_confirm = "TestPass123!"
    first_name = "Anna"
    last_name = "Petrova"
    role = "trainer"
    company_name = "Yoga Studio Harmony"
    tax_id = "5555555555"
} | ConvertTo-Json

Write-Host "Sending B2B registration request (attempt 3 - with fixed env)..." -ForegroundColor Cyan

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
    Write-Host "Check your Gmail inbox (alex.mobicraft@gmail.com) for admin notification!" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "ERROR during registration:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
