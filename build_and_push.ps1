Set-Location "C:\Users\info\Desktop\dev\tools\projects\ai-daily-jp"

Write-Host "Building Astro..." -ForegroundColor Cyan
Set-Location astro-site
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location ..
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git add .
$date = Get-Date -Format "yyyy-MM-dd HH:mm"
git commit -m "Auto update $date"
git push origin main

Write-Host "Done!" -ForegroundColor Green
Start-Sleep -Seconds 2
