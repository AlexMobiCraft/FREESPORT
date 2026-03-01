# Powershell script to merge develop into main and push to GitHub

# Set error action to stop on errors
$ErrorActionPreference = "Stop"

try {
    Write-Host "--- Starting deployment from develop to main ---" -ForegroundColor Cyan

    # 1. Fetch latest changes
    Write-Host "Step 1: Fetching all branches..." -ForegroundColor Yellow
    git fetch origin

    # 2. Ensure we are on develop and have latest changes
    Write-Host "Step 2: Updating local 'develop' branch..." -ForegroundColor Yellow
    git checkout develop
    git pull origin develop

    # 3. Switch to main and update it
    Write-Host "Step 3: Updating local 'main' branch..." -ForegroundColor Yellow
    git checkout main
    git pull origin main

    # 4. Merge develop into main
    Write-Host "Step 4: Merging 'develop' into 'main'..." -ForegroundColor Yellow
    git merge develop --no-edit

    # 5. Push changes to GitHub
    Write-Host "Step 5: Pushing 'main' to origin..." -ForegroundColor Yellow
    git push origin main

    # 6. Return to develop
    Write-Host "Step 6: Returning to 'develop' branch..." -ForegroundColor Yellow
    git checkout develop

    Write-Host "--- Successfully merged and pushed to main ---" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Deployment failed. Please check for merge conflicts or connection issues." -ForegroundColor Red
    exit 1
}
