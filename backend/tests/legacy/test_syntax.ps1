# Simple syntax test for PowerShell script
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [console]::InputEncoding = [console]::OutputEncoding = New-Object System.Text.UTF8Encoding

Write-Host "Testing PowerShell script syntax..." -ForegroundColor Green

# Test variables
$BASE_URL = "http://127.0.0.1:8001/api/v1"
$TEST_EMAIL = "test@example.com"
$TOTAL_TESTS = 0
$PASSED_TESTS = 0

Write-Host "Base URL: $BASE_URL" -ForegroundColor Yellow
Write-Host "Test Email: $TEST_EMAIL" -ForegroundColor Yellow

# Test JSON creation
$testData = @{
    email = $TEST_EMAIL
    password = "TestPassword123!"
    role = "retail"
} | ConvertTo-Json

Write-Host "JSON Test Data:" -ForegroundColor Cyan
Write-Host $testData -ForegroundColor White

# Test array and hashtable
$headers = @{ Authorization = "Bearer test-token" }
Write-Host "Headers created successfully" -ForegroundColor Green

# Test conditional logic
if ($TOTAL_TESTS -eq 0) {
    Write-Host "[PASS] Conditional logic works" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Conditional logic failed" -ForegroundColor Red
}

Write-Host "PowerShell syntax test completed successfully!" -ForegroundColor Green
