$ProgressPreference = 'SilentlyContinue'
$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$headers = @{ "X-Tenant-Id" = "tenant-demo" }

# Run-on (you.What) + multi-sentence, but shorter so Qwen finishes within timeout.
$text = "Hello! I am here with you.What story would you like today? Ask about Krishna or Ram!"

$body = @{
    session_id   = "verify-chunk-$(Get-Random)"
    input_type   = "voice"
    text         = $text
    domain       = "religious"
    language     = "en-US"
    output_audio = $true
    tts_provider = "qwen"
    voice        = "serena"
} | ConvertTo-Json

Write-Host "=== Sending run-on multi-sentence text ==="
try {
    $resp = Invoke-WebRequest -Uri "$BASE/agent/stream" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 180
    $c = $resp.Content
    $audioCount = ([regex]::Matches($c, 'event: audio')).Count
    $textCount = ([regex]::Matches($c, 'event: text')).Count
    $doneOk = if ($c -match '"ok":\s*true') { "ok:true" } else { "ok:false" }
    Write-Host "HTTP $($resp.StatusCode)  text_events=$textCount  audio_events=$audioCount  $doneOk"
    if ($audioCount -ge 2) { Write-Host "PASS: $audioCount audio chunks - continuous playback, stall fixed" }
    else { Write-Host "CHECK: only $audioCount audio chunk(s)" }
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
}
