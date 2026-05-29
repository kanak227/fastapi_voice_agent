$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$headers = @{ "X-Tenant-Id" = "tenant-demo" }

function Test-Tts($label, $voice, $lang, $text) {
    $body = @{
        text         = $text
        language     = $lang
        tts_provider = "qwen"
        voice        = $voice
        output_format = "mp3_44100_128"
    } | ConvertTo-Json
    Write-Host "=== $label (voice=$voice lang=$lang) ==="
    try {
        $resp = Invoke-WebRequest -Uri "$BASE/voice/synthesize" -Method POST -Body $body -ContentType "application/json" -Headers $headers -UseBasicParsing -TimeoutSec 90
        $len = $resp.RawContentLength
        if ($len -eq 0) { $len = $resp.Content.Length }
        Write-Host "  HTTP $($resp.StatusCode)  ContentType=$($resp.Headers['Content-Type'])  bytes=$len"
    } catch {
        Write-Host "  ERROR HTTP $($_.Exception.Response.StatusCode.value__)"
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            Write-Host "  BODY: $($reader.ReadToEnd())"
        }
    }
}

# ASCII-safe cases through Cloud Run (voice selection + Hinglish romanized input)
Test-Tts "Serena EN" "serena" "en-US" "Hello, this is a test of the offline voice."
Test-Tts "Ryan EN"   "ryan"   "en-US" "Hello, this is a test of the offline voice."
Test-Tts "Hinglish"  "mms-hindi" "hi-Latn" "namaste aap kaise hain"
