# Как импорт изображений работает сейчас

Точки в коде на коммит `1c0fac85`. Всё основное — в `backend/apps/products/services/variant_import.py`.

## Два пути импорта картинок

**Путь на проде — только XML.** Список картинок берёт парсер из тегов `<Картинка>` (`services/parser.py:313` для goods, `:364` для offers) и кладёт в `goods_data["images"]`. Оттуда:

- `_import_base_images` — вызовы на `variant_import.py:556` и `:614`;
- `_import_variant_images` — вызовы на `:830` и `:917`.

**Второй путь — сканирование каталога глобом по `onec_id`** (`management/commands/import_images_from_1c.py`, `integrations/tasks.py:192`) — **на проде не исполняется**: сессий с `import_type='images'` в базе ноль.

## `_import_base_images` (`:647`) — аддитивен

Существующий список предзагружается в `base_images` / `seen_filenames` (`:665-675`), новые пути дописываются в хвост (`:694`). Удаления нет, переупорядочивания нет. Сравнение на `:703` фиксирует только факт роста списка.

## `_import_variant_images` (`:934`) — аддитивен и не переназначает главное

`main_image_set = bool(variant.main_image)` (`:949`), далее `if not main_image_set` (`:987`). Уже заполненное главное изображение заменить нельзя конструктивно — этот запрет снимается вместе с зеркалированием состава товара, иначе поведение товара и варианта разъедется.

## `_save_image_if_not_exists` (`:380`) — источник ложных ошибок

Копирует файл, если его ещё нет в хранилище (`:426`), и **считает ошибкой отсутствие исходника** (`:403-406`) — даже когда копия давно лежит в `media`. Это и есть источник 253 ошибок на прогон: 1С подчищает `import_files` после импорта (`import_products_from_1c.py:878-904`), а `goods.xml` с теми же товарами приходит снова.

Skip на `:426` срабатывает по факту существования имени файла, без сравнения содержимого. Ни сравнения размера, ни `mtime`, ни хэша: `grep hashlib|md5|st_mtime|checksum` по файлу — 0 совпадений. Флагов `--force` / `--overwrite` нет ни в одной команде импорта. `_clear_existing_data` (`import_products_from_1c.py:907`) чистит только записи БД, `media` не трогает.

## Порог размера

`MIN_IMAGE_SIZE_BYTES = 100 КБ` (`:358`), резервный `FALLBACK_MIN_IMAGE_SIZE_BYTES = 8 КБ` (`:360`), выбор — `_get_effective_min_size` (`:362`), и он смотрит **только на исходники**. Мелкое превью, попавшее раньше по резервному порогу, остаётся в составе навсегда и первым.

## Наблюдаемость

Счётчики `images_copied` / `images_skipped` / `images_errors` пишутся в `report_details` (`variant_import.py:2311`). Текстовый `report` сессии про изображения не пишет ничего: `report ILIKE '%изображен%'` по всей таблице — 0 строк.

## `Path(variant.main_image)` (`:958`)

`main_image` — `ImageField`; `Path()` от `ImageFieldFile` кидает `TypeError: argument should be a str or an os.PathLike object`. Ветка достижима в аддитивном режиме при непустом `main_image` — то есть в команде `import_images_from_1c` на товаре, у которого главное фото уже стоит. Резать путь нужно по `.name`.

## Готовый инструмент для исторической чистки

`python manage.py deduplicate_images --min-size 100` удаляет из `base_images` файлы мельче порога, а у вариантов заменяет мелкий `main_image` на первый подходящий из галереи (`deduplicate_images.py:173-186`, `:285-292`). Защита от обнуления есть: если после фильтрации не осталось ничего, первый файл возвращается (`:179-184`). На проде, судя по 104 живым случаям, её ни разу не запускали — сначала `--dry-run`.

## Blast radius

На 27.08.2026 `npx gitnexus impact` по обоим методам импорта — **LOW**, 9 узлов, 4 прямых вызывающих. Проверять заново перед правкой: `npx gitnexus impact <symbol> --direction upstream` для `_import_base_images`, `_import_variant_images`, `_save_image_if_not_exists`, `_get_effective_min_size`.
