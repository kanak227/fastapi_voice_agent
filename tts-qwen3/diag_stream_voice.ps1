$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$headers = @{ "X-Tenant-Id" = "tenant-demo" }

# Mimic the agent/stream voice path with output_audio + tts_provider=qwen + a specific voice.
function Test-Stream($label, $voice) {
    $body = @{
        session_id   = "diag-$label-$(Get-Random)"
        input_type   = "voice"
        text         = "Tell me about Krishna in two sentences."
        domain       = "religious"
        language     = "en-US"
        output_audio = $true
        tts_provider = "qwen"
        tts_voice    = $voice
    } | ConvertTo-Json

    Write-Host "=== $label (tts_voice=$voice) ==="
    try {
        $resp = Invoke-WebRequest -Uri "$BASE/agent/stream" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 200
        $c = $resp.Content
        # Count audio events and total audio_b64 length
        $audioCount = ([regex]::Matches($c, 'event: audio')).Count
        $m = [regex]::Matches($c, '"audio_b64":\s*"([^"]+)"')
        $total = 0
        foreach ($x in $m) { $total += $x.Groups[1].Value.Length }
        $doneOk = if ($c -match '"ok":\s*true') { "ok:true" } else { "ok:false" }
        Write-Host "  HTTP $($resp.StatusCode)  audio_events=$audioCount total_b64=$total  $doneOk"
    } catch {
        Write-Host "  ERROR HTTP $($_.Exception.Response.StatusCode.value__)"
    }
}

Test-Stream "serena" "serena"
Test-Stream "ryan" "ryan"
