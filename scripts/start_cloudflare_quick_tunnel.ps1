param(
    [string]$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$serverProc = $null
$tunnelProc = $null

if ($ProjectRoot -match "\s-(HostAddress|Port)\b") {
    $ProjectRoot = ($ProjectRoot -replace "\s-(HostAddress|Port)\b.*$", "").Trim()
}

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Invalid ProjectRoot path: $ProjectRoot"
}

function Get-CloudflaredPath {
    param([string]$RootPath)

    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }

    $vendorDir = Join-Path $RootPath "third_party\cloudflared"
    $vendorExe = Join-Path $vendorDir "cloudflared.exe"

    if (Test-Path $vendorExe) {
        return $vendorExe
    }

    New-Item -ItemType Directory -Path $vendorDir -Force | Out-Null
    $downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    Write-Host "cloudflared not found, downloading from official release..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $vendorExe
    return $vendorExe
}

function Wait-Health {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 25
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod -Uri $Url -TimeoutSec 2
            if ($resp.ok -eq $true) {
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Wait-TunnelUrl {
    param(
        [string]$LogFile,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $pattern = "https://[a-z0-9-]+\.trycloudflare\.com"

    while ((Get-Date) -lt $deadline) {
        if (Test-Path $LogFile) {
            $content = Get-Content $LogFile -ErrorAction SilentlyContinue
            if ($content) {
                $match = [regex]::Match(($content -join "`n"), $pattern)
                if ($match.Success) {
                    return $match.Value
                }
            }
        }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

Push-Location $ProjectRoot
try {
    if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = "minimax" }
    if (-not $env:MINIMAX_MODEL) { $env:MINIMAX_MODEL = "MiniMax-M2.5" }
    if (-not $env:MINIMAX_BASE_URL) { $env:MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic" }
    if (-not $env:WEB_AUTH_ENABLED) { $env:WEB_AUTH_ENABLED = "1" }
    if (-not $env:WEB_USERNAME) { $env:WEB_USERNAME = "admin" }
    if (-not $env:WEB_PASSWORD) { $env:WEB_PASSWORD = "ChangeMe_2026" }

    if (-not $env:MINIMAX_API_KEY) {
        Write-Host "Warning: MINIMAX_API_KEY is empty, model calls may fail." -ForegroundColor Yellow
    }

    $logsDir = Join-Path $ProjectRoot "logs"
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

    $cloudflaredExe = Get-CloudflaredPath -RootPath $ProjectRoot
    $localUrl = "http://$HostAddress`:$Port"
    $healthUrl = "$localUrl/api/health"
    $tunnelLog = Join-Path $logsDir "cloudflared.log"
    if (Test-Path $tunnelLog) { Remove-Item $tunnelLog -Force }

    Write-Host ""
    Write-Host "Starting local server at $localUrl"
    Write-Host "Web username: $($env:WEB_USERNAME)"
    Write-Host "Web password: $($env:WEB_PASSWORD)"
    Write-Host ""

    $serverArgs = @("server.py", "--host", $HostAddress, "--port", "$Port")
    $serverProc = Start-Process -FilePath "python" -ArgumentList $serverArgs -WorkingDirectory $ProjectRoot -PassThru

    if (-not (Wait-Health -Url $healthUrl -TimeoutSeconds 25)) {
        throw "Local server health check failed: $healthUrl"
    }

    Write-Host "Starting Cloudflare quick tunnel..."
    $cfArgs = @(
        "tunnel",
        "--url", $localUrl,
        "--logfile", $tunnelLog,
        "--loglevel", "info"
    )
    $tunnelProc = Start-Process -FilePath $cloudflaredExe -ArgumentList $cfArgs -WorkingDirectory $ProjectRoot -PassThru

    $publicUrl = Wait-TunnelUrl -LogFile $tunnelLog -TimeoutSeconds 45
    if ($publicUrl) {
        Write-Host ""
        Write-Host "Public URL: $publicUrl" -ForegroundColor Green
        Write-Host "You can access this URL from home and office."
        Set-Content -Path (Join-Path $logsDir "cloudflare_public_url.txt") -Value $publicUrl -Encoding UTF8
    }
    else {
        Write-Host "Public URL not detected yet. Check logs\cloudflared.log" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Press Ctrl+C to stop both server and tunnel."
    Wait-Process -Id $tunnelProc.Id
}
finally {
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}
