$BASE = "https://multi-bot-server-650841589964.us-central1.run.app"
$langs = @("en-US","hi","hi-Latn","ta","te","mr","bn","gu","kn","ml","pa","fr","de","es","ar","zh","ja")
foreach ($l in $langs) {
    try {
        $c = (Invoke-WebRequest -Uri "$BASE/voice/voices?tts_provider=qwen&language=$l" -UseBasicParsing -TimeoutSec 30).Content
        $arr = $c | ConvertFrom-Json
        $names = ($arr | ForEach-Object { $_.voice_id }) -join ", "
        $count = $arr.Count
        if ($count -eq 0) { Write-Host "$l => EMPTY" }
        else { Write-Host "$l => $count : $names" }
    } catch {
        Write-Host "$l => ERROR $($_.Exception.Message)"
    }
}
