Write-Host "--- Uruchamianie środowiska Lab ---" -ForegroundColor Cyan
docker compose up --build -d
Write-Host "`nStatus kontenerów:" -ForegroundColor Yellow
docker compose ps
Write-Host "`n[GOTOWE] Możesz teraz uruchomić aplikację Java (Launcher.java)." -ForegroundColor Green