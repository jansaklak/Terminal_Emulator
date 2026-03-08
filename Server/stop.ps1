Write-Host "--- Zatrzymywanie środowiska Lab ---" -ForegroundColor Cyan
docker compose down
$runningMysql = docker ps -q --filter "ancestor=mysql:8.0"
if ($runningMysql) {
    Write-Host "Sprzątanie pozostałych sesji MySQL..." -ForegroundColor Gray
    docker stop $runningMysql
}
docker network prune -f
Write-Host "`n[GOTOWE] Środowisko zostało całkowicie wyczyszczone." -ForegroundColor Green