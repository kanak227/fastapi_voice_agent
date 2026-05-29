$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$headers = @{ "X-Tenant-Id" = "tenant-demo" }

function Test-Tts($label, $voice, $lang, $text) {
    $b = @{ text = $text; language = $lang; tts_provider = "qwen" }
    if ($voice) { $b.voice = $voice }
    $body = $b | ConvertTo-Json
    Write-Host "=== $label (voice=$voice lang=$lang len=$($text.Length)) ==="
    try {
        $resp = Invoke-WebRequest -Uri "$BASE/voice/synthesize" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 120
        $d = $resp.Content | ConvertFrom-Json
        $alen = if ($d.audio_b64) { $d.audio_b64.Length } else { 0 }
        Write-Host "  HTTP $($resp.StatusCode) voice=$($d.voice) mime=$($d.mime_type) audio_b64_len=$alen"
    } catch {
        Write-Host "  ERROR HTTP $($_.Exception.Response.StatusCode.value__)"
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host "  BODY: $($reader.ReadToEnd())"
        }
    }
}

# Default voice (no voice field) - what religious bot likely sends when voiceId is empty
Test-Tts "Default EN short" "" "en-US" "Krishna is a Hindu deity."
# Longer multi-sentence
Test-Tts "Default EN long" "" "en-US" "Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna on the battlefield of Kurukshetra."
# Explicit voice
Test-Tts "Serena EN long" "serena" "en-US" "Krishna is a principal deity in Hinduism. He is revered as the eighth avatar of Vishnu. He delivered the teachings of the Bhagavad Gita to Arjuna."
