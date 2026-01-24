
$baseUrl = "https://freesport.ru/api/integration/1c/exchange/"
$cookieFile = "cookies_remote.txt"
$auth = "1c_exchange_robot@freesport.ru:20.robot.20"
$testFile = "data/import_1c/priceLists/priceLists_1_1_6e305b99-b33f-403d-a401-f5aaae62fbc3.xml"
$remoteFilename = "test_import.xml"

Write-Host "--- Step 1: Authorization ---" -ForegroundColor Cyan
$authUrl = $baseUrl + "?mode=checkauth"
curl.exe -s -c $cookieFile -u $auth "$authUrl"

Write-Host "`n--- Step 2: Initialization ---" -ForegroundColor Cyan
$initUrl = $baseUrl + "?mode=init"
curl.exe -s -b $cookieFile "$initUrl"

Write-Host "`n--- Step 3: File Upload ---" -ForegroundColor Cyan
if (Test-Path $testFile) {
    # We must quote the URL carefully because of the '&'
    $fileUrl = $baseUrl + "?mode=file&filename=$remoteFilename"
    curl.exe -s -b $cookieFile -X POST --data-binary "@$testFile" "$fileUrl"
}
else {
    Write-Host "ERROR: Local file $testFile not found!" -ForegroundColor Red
}

Write-Host "`n--- Step 4: Start Import ---" -ForegroundColor Cyan
$importUrl = $baseUrl + "?mode=import&filename=$remoteFilename"
curl.exe -s -b $cookieFile "$importUrl"

Write-Host "`n--- FINISHED ---" -ForegroundColor Green
Write-Host "To check results on server run:"
Write-Host "docker compose exec backend python scripts/check_last_session.py"
