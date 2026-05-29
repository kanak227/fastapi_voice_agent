$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$headers = @{ "X-Tenant-Id" = "tenant-demo" }
$domains = @("education", "financial-literacy", "wellbeing", "entrepreneurship")

foreach ($d in $domains) {
    $body = @{
        session_id   = "smoke-$d-$(Get-Random)"
        input_type   = "text"
        text         = "Give me one short tip."
        domain       = $d
        language     = "en-US"
        output_audio = $false
    } | ConvertTo-Json

    Write-Host "=== $d ==="
    try {
        $resp = Invoke-WebRequest -Uri "$BASE/agent/stream" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 90
        $c = $resp.Content
        if ($c -match '"ok": true') { Write-Host "  PASS (ok:true)" }
        elseif ($c -match 'stream_failed') { Write-Host "  FAIL (stream_failed)" }
        else { Write-Host "  ? $($c.Substring(0,[Math]::Min(200,$c.Length)))" }
    } catch {
        Write-Host "  ERROR HTTP $($_.Exception.Response.StatusCode.value__)"
    }
}
