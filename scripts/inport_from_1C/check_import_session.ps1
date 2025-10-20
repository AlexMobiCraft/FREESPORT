param(
    [string]$ComposeFile = "docker-compose.test.yml",
    [int]$Last = 5
)

Write-Host "Получение последних сессий импорта..."
docker compose -f $ComposeFile run --rm backend python manage.py shell -c "from apps.products.models import ImportSession; sessions = ImportSession.objects.order_by('-started_at')[:$Last];
print('Всего найдено сессий:', sessions.count());
for session in sessions:
    print('ID:', session.id)
    print('Статус:', session.status)
    print('Тип:', session.import_type)
    print('Начало:', session.started_at)
    print('Окончание:', session.finished_at)
    print('Детали:', session.report_details)
    print('-' * 40)
"
