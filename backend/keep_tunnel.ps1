while ($true) {
    Write-Host "[TUNNEL SUPERVISOR] Launching localtunnel for technexa-safety-2026.loca.lt on port 8000..."
    npx -y localtunnel --port 8000 --subdomain technexa-safety-2026
    Write-Host "[TUNNEL SUPERVISOR] Tunnel disconnected. Reconnecting in 3s..."
    Start-Sleep -Seconds 3
}
