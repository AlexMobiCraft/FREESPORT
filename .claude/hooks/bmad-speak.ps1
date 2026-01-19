param(
    [string]$AgentId,
    [string]$Text
)

# Очистка текста от лишних кавычек, если они передались
$TextClean = $Text.Trim("'").Trim('"')
$AgentIdClean = $AgentId.Trim("'").Trim('"')

try {
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.SetOutputToDefaultAudioDevice()
    
    # Получаем список доступных голосов
    $voices = $synth.GetInstalledVoices().VoiceInfo
    
    if ($voices.Count -gt 0) {
        # Простая логика выбора голоса на основе имени агента, чтобы они звучали по-разному
        # Преобразуем имя в число для выбора индекса
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($AgentIdClean)
        $seed = 0
        foreach ($b in $bytes) { $seed += $b }
        
        $voiceIndex = $seed % $voices.Count
        $synth.SelectVoice($voices[$voiceIndex].Name)
    }

    # Говорим
    $synth.Speak($TextClean)
} catch {
    Write-Host "TTS Error: $_"
}
