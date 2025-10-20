# Script to update the FREESPORT project code on server 192.168.1.130
# Usage (works with the current branch by default):
#   pwsh .\scripts\update_server_code.ps1
#   pwsh .\scripts\update_server_code.ps1 -Branch feature/x -EnvFileLocal "backend/.env.test"
#   pwsh .\scripts\update_server_code.ps1 -User alex -IP 192.168.1.130
# Before running, make sure local changes are committed and pushed to origin if necessary.

param(
    [string]$User = "alex",
    [string]$IP = "192.168.1.130",
    [string]$ProjectPathRemote = "~/FREESPORT",
    [string]$DockerContext = "freesport-remote",
    [string]$ComposeFile = "docker-compose.test.yml",
    [string]$EnvFileLocal = "backend/.env",
    [string]$EnvFileRemote = "~/FREESPORT/backend/.env",
    [string]$SshKeyPath = "backend\\.ssh\\id_ed25519",
    [string]$Branch
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8

# Function to start ssh-agent and add the specified private key
function Start-SshAgentIfNeeded {
    param(
        [string]$KeyPath
    )

    if (-not (Test-Path -Path $KeyPath)) {
        throw "SSH key not found: $KeyPath"
    }

    Start-Service ssh-agent -ErrorAction SilentlyContinue | Out-Null
    ssh-add $KeyPath | Out-Null
}

# Function to determine the current git branch in the specified directory
function Get-CurrentGitBranch {
    param(
        [string]$WorkingDirectory
    )

    $branch = (git -C $WorkingDirectory rev-parse --abbrev-ref HEAD).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw 'Could not determine the current git branch'
    }

    return $branch
}

# Function to perform git fetch/pull on the server via SSH
function Invoke-RemoteGitUpdate {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$RemotePath,
        [string]$BranchName
    )

    $remoteCommand = "cd $RemotePath; git fetch origin; git checkout $BranchName; git pull --ff-only origin $BranchName; git status"
    ssh "$ConnectionUser@$ConnectionHost" $remoteCommand
}

# Function to copy a local .env file to the server via SCP
function Copy-EnvFileToServer {
    param(
        [string]$ConnectionUser,
        [string]$ConnectionHost,
        [string]$LocalPath,
        [string]$RemotePath
    )

    if (-not (Test-Path -Path $LocalPath)) {
        throw "Local file not found: $LocalPath"
    }

    scp $LocalPath ([string]::Format('{0}@{1}:{2}', $ConnectionUser, $ConnectionHost, $RemotePath));
}

# Function to restart test containers via docker compose in a remote context
function Restart-RemoteCompose {
    param(
        [string]$Context,
        [string]$ComposeFilePath
    )

    & docker --context $Context compose -f $ComposeFilePath down -v
    & docker --context $Context compose -f $ComposeFilePath up -d
}

$scriptDirectory = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$projectRoot = (Resolve-Path (Join-Path $scriptDirectory '..\..')).Path

Push-Location $projectRoot

try {
    Write-Host '=== Updating code on the server ===' -ForegroundColor Cyan

    $absoluteSshKeyPath = if ([System.IO.Path]::IsPathRooted($SshKeyPath)) { $SshKeyPath } else { Join-Path -Path $projectRoot -ChildPath $SshKeyPath }
    Start-SshAgentIfNeeded -KeyPath $absoluteSshKeyPath

    if (-not $Branch) {
        $Branch = Get-CurrentGitBranch -WorkingDirectory $projectRoot
    }
    Write-Host "Using branch: $Branch" -ForegroundColor Yellow

    Write-Host 'Updating code on the server...' -ForegroundColor Yellow
    Invoke-RemoteGitUpdate -ConnectionUser $User -ConnectionHost $IP -RemotePath $ProjectPathRemote -BranchName $Branch

    $absoluteEnvPath = if ([System.IO.Path]::IsPathRooted($EnvFileLocal)) { $EnvFileLocal } else { Join-Path -Path $projectRoot -ChildPath $EnvFileLocal }
    Write-Host 'Syncing .env file...' -ForegroundColor Yellow
    Copy-EnvFileToServer -ConnectionUser $User -ConnectionHost $IP -LocalPath $absoluteEnvPath -RemotePath $EnvFileRemote

    Write-Host "Restarting docker compose in context '$DockerContext'..." -ForegroundColor Yellow
    $composeProjectRoot = $ProjectPathRemote
    if ($ProjectPathRemote.StartsWith("~/", [System.StringComparison]::Ordinal)) {
        $composeProjectRoot = "/home/$User/" + $ProjectPathRemote.Substring(2)
    }

    $previousProjectRoot = $env:FREESPORT_PROJECT_ROOT
    try {
        $env:FREESPORT_PROJECT_ROOT = $composeProjectRoot
        Restart-RemoteCompose -Context $DockerContext -ComposeFilePath $ComposeFile
    }
    finally {
        if ($null -eq $previousProjectRoot) {
            Remove-Item Env:FREESPORT_PROJECT_ROOT -ErrorAction SilentlyContinue
        }
        else {
            $env:FREESPORT_PROJECT_ROOT = $previousProjectRoot
        }
    }

    Write-Host '✓ Update complete' -ForegroundColor Green
}
catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Pop-Location
}
