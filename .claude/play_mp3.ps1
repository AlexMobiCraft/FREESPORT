# Замените 'C:\Путь\к\вашему\файлу.mp3' на реальный путь к файлу
$filePath = "C:\Users\38670\.claude\Stop.mp3"

# Проверяем, существует ли файл
if (Test-Path -Path $filePath) {
    # Запускаем процесс для открытия файла
    Start-Process -FilePath 'C:\Users\38670\.claude\Stop.mp3'
} else {
    Write-Host "Файл не найден по указанному пути: $filePath" -ForegroundColor Red
}