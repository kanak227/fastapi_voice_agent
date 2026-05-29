$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$body = @{
    session_id = "smoke-test-$(Get-Random)"
    input_type = "text"
    text       = "Who is Krishna? Answer in one sentence."
    domain     = "religious"
    language   = "en-US"
    output_audio = $false
} | ConvertTo-Json

Write-Host "=== POST /agent/stream (religious) ==="
Write-Host "BODY: $body"
try {
    $headers = @{ "X-Tenant-Id" = "tenant-demo" }
    $resp = Invoke-WebRequest -Uri "$BASE/agent/stream" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 90
    Write-Host "HTTP $($resp.StatusCode)"
    $resp.Content.Substring(0, [Math]::Min(2000, $resp.Content.Length))
} catch {
    Write-Host "HTTP STATUS: $($_.Exception.Response.StatusCode.value__)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "RESPONSE BODY:"
        $reader.ReadToEnd()
    } else {
        Write-Host "ERROR: $($_.Exception.Message)"
    }
}
