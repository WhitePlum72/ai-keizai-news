# publish.ps1 — AI経済新聞 記事公開パイプライン
$ErrorActionPreference = "Stop"
$ProjectDir = "C:\Users\info\Desktop\dev\tools\projects\ai-daily-jp"
$ComfyUIPath = "C:\Users\info\Desktop\dev\tools\ComfyUI\main.py"

Set-Location $ProjectDir

$null = New-Item -ItemType Directory -Force -Path "logs"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "$ProjectDir\logs\publish_$Timestamp.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Line = "$(Get-Date -Format 'HH:mm:ss') [$Level] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line -Encoding UTF8
}

function Run-Step {
    param([string]$Label, [string]$Script, [bool]$AllowFail = $false)
    Write-Log ""
    Write-Log ">>> $Label 開始"
    $proc = Start-Process python -ArgumentList $Script `
        -NoNewWindow -PassThru `
        -RedirectStandardOutput "logs\_stdout.tmp" `
        -RedirectStandardError  "logs\_stderr.tmp"
    $lastPos = 0
    while (-not $proc.HasExited) {
        Start-Sleep -Milliseconds 500
        if (Test-Path "logs\_stdout.tmp") {
            $content = Get-Content "logs\_stdout.tmp" -Raw -ErrorAction SilentlyContinue
            if ($content -and $content.Length -gt $lastPos) {
                $content.Substring($lastPos) -split "`n" | Where-Object { $_.Trim() } | ForEach-Object { Write-Log "  $_" }
                $lastPos = $content.Length
            }
        }
    }
    foreach ($f in @("logs\_stdout.tmp","logs\_stderr.tmp")) {
        if (Test-Path $f) {
            Get-Content $f | Where-Object { $_.Trim() } | ForEach-Object { Write-Log "  $_" }
            Remove-Item $f -Force
        }
    }
if (($proc.ExitCode -ne $null) -and ($proc.ExitCode -ne 0) -and -not $AllowFail) {
        Write-Log "[$Label] 失敗 (exit $($proc.ExitCode))" "ERROR"
        throw "$Label が失敗しました"
    }
    Write-Log ">>> $Label 完了"
}

try {
    Write-Log "============================================================"
    Write-Log " AI経済新聞 記事公開パイプライン"
    Write-Log " ログ: $LogFile"
    Write-Log "============================================================"

    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^(\w+)=(.+)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
        }
    }

    Run-Step "[1/6] RSS収集"      "collector.py"
    Run-Step "[2/6] スコアリング" "scorer.py"
    Run-Step "[3/6] 記事生成"     "translator.py"

    Write-Log ""
    Write-Log ">>> [4/6] ComfyUI起動中..."
    $comfy = Start-Process python -ArgumentList $ComfyUIPath -WindowStyle Minimized -PassThru
    Write-Log "  起動待機中（20秒）..."
    Start-Sleep -Seconds 20
    Write-Log ">>> [4/6] ComfyUI起動完了"

    Run-Step "[5/6] 画像生成" "image_generator.py" -AllowFail $true

    if ($comfy -and -not $comfy.HasExited) { $comfy.Kill(); Write-Log "  ComfyUI停止" }

    Run-Step "[6/6] 記事公開" "publisher.py"

    Write-Log ""
    Write-Log ">>> Astroビルド中..."
    Set-Location "$ProjectDir\astro-site"
    $buildOut = npm run build 2>&1
    $buildOut | ForEach-Object { Write-Log "  $_" }
    if ($LASTEXITCODE -ne 0) { throw "npm run build 失敗" }
    Set-Location $ProjectDir
    Write-Log ">>> Astroビルド完了"

    Write-Log ""
    Write-Log "============================================================"
    Write-Log " 全工程完了！ $(Get-Date -Format 'HH:mm:ss')"
    Write-Log " ログ: $LogFile"
    Write-Log "============================================================"
    Start-Sleep -Seconds 5

} catch {
    Write-Log ""
    Write-Log "============================================================" "ERROR"
    Write-Log " 停止: $_" "ERROR"
    Write-Log " ログ: $LogFile" "ERROR"
    Write-Log "============================================================" "ERROR"
    Read-Host "Enterキーで閉じます"
    exit 1
}

