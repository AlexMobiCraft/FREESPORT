# Исправление: Ошибка импорта остатков

## Проблема

При импорте остатков возникала ошибка:

```
FileNotFoundError: Файл остатков не найден: /app/data/import_1c/rests/rests.xml
```

## Причина

В директории `/app/data/import_1c/rests/` находятся файлы с паттерном `rests_1_*.xml`:

- `rests_1_1_bf987153-7db9-4af6-818e-07f3f1b97bc8.xml`
- `rests_1_2_90725d2f-8e88-49f1-bd46-666d3beb05d2.xml`
- `rests_1_3_bbfef6e3-a9e4-482a-ace3-5095192524c9.xml`
- и т.д.

Код в `tasks.py` искал один файл `rests.xml`, который не существует.

## Решение

Изменена логика импорта остатков в `backend/apps/integrations/tasks.py`:

### Было:

```python
elif import_type == "stocks":
    file_path = data_path / "rests" / "rests.xml"
    if not file_path.exists():
        raise FileNotFoundError(...)

    call_command("load_product_stocks", "--file", str(file_path))
```

### Стало:

```python
elif import_type == "stocks":
    rests_dir = data_path / "rests"
    if not rests_dir.exists():
        raise FileNotFoundError(...)

    call_command(
        "import_catalog_from_1c",
        "--data-dir", str(data_dir),
        "--file-type", "rests",
    )
```

## Преимущества нового подхода

✅ **Обрабатывает все файлы** - команда `import_catalog_from_1c` с `--file-type=rests` автоматически находит и обрабатывает все файлы `rests*.xml`  
✅ **Единообразие** - используется та же команда, что и для импорта каталога и цен  
✅ **Прогресс-бар** - показывает прогресс обработки каждого файла  
✅ **Логирование** - детальные логи обработки

## Тестирование

### Шаг 1: Запустите импорт остатков

1. Откройте `http://localhost:8001/admin/integrations/integrationimportsession/`
2. Нажмите "🚀 Запустить импорт из 1С"
3. Выберите **ТОЛЬКО "Остатки товаров"**
4. Нажмите "▶️ Запустить импорт"

### Шаг 2: Проверьте логи Celery

```powershell
docker-compose -f docker/docker-compose.yml logs -f celery
```

Вы должны увидеть:

```
[Task <task_id>] Запуск выборочного импорта: ['stocks']
[Task <task_id>] Начало импорта: stocks
[Task <task_id>] Запуск import_catalog_from_1c --file-type=rests
📊 Шаг 5: Обновление остатков из rests.xml...
   Обработка rests_1_1_*.xml: 100%|██████████| 1234/1234
   Обработка rests_1_2_*.xml: 100%|██████████| 1234/1234
   ...
[Task <task_id>] Импорт stocks завершен: Остатки обновлены
```

### Шаг 3: Проверьте результат

Импорт должен завершиться успешно без ошибки `FileNotFoundError`.

## Структура данных 1С

Убедитесь, что в директории `data/import_1c/rests/` присутствуют XML файлы:

```
data/import_1c/rests/
├── rests_1_1_<uuid>.xml
├── rests_1_2_<uuid>.xml
├── rests_1_3_<uuid>.xml
├── rests_1_4_<uuid>.xml
└── rests_1_5_<uuid>.xml
```

Команда `import_catalog_from_1c` автоматически найдет и обработает все эти файлы.

## Деплой на продакшн

### Локально

```powershell
# Перезапустить Celery worker
docker-compose -f docker/docker-compose.yml restart celery
```

### Продакшн

```bash
ssh root@5.35.124.149
cd /root/freesport

# Перезапустить Celery worker
docker-compose -f docker/docker-compose.prod.yml restart celery
```

## Измененные файлы

1. ✅ `backend/apps/integrations/tasks.py` - изменена логика импорта остатков

## Связанные команды

- `import_catalog_from_1c --file-type=rests` - импорт остатков (используется теперь)
- `load_product_stocks --file <path>` - импорт из одного файла (устарело для этого случая)

## Контакты

При возникновении проблем обращайтесь к разработчику:

- **Developer:** James (Dev Agent)
- **Fix:** Импорт остатков из множественных файлов
- **Date:** 2025-11-04
