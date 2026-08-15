#!/usr/bin/env bash
# ============================================================================
# prep-1c-test-data.sh — упаковка реальных выгрузок 1С в приватный data-репо
# ============================================================================
#
# Назначение:
#   Собирает каталоги реальных XML-выгрузок 1С, нужные data_dependent-тестам,
#   и пушит их в приватный репозиторий GitHub. Этот репо подключается в CI
#   (main.yml) через секрет 1C_DATA_TOKEN, чтобы ~32 теста импорта 1С
#   исполнялись на раннере, а не скипались.
#
# Что попадает в data-репо (только то, что нужно тестам):
#   contragents/            — 7 файлов, ~8 МБ (test_customer_parser, test_link_then_import)
#   contragents_pricetype/  — 10 файлов, ~13 МБ (test_import_role, test_link_applies_role,
#                             test_import_customers_price_type, test_customers_price_type_detector,
#                             test_customer_processor)
#   priceLists/             — 1 файл, ~0.01 МБ (test_import_opt4_prices)
#   prices/                 — 8 файлов, ~27 МБ (test_import_opt4_prices)
#   Итого: ~48 МБ
#
# Что НЕ попадает (синтетические тесты не используют):
#   goods/, offers/, rests/, units/, storages/, propertiesGoods/, propertiesOffers/,
#   import_1c/, groups/ — не нужны data_dependent-тестам и раздули бы репо.
#
# Предупреждение:
#   Репо приватный. Данные содержат ФИО, ИНН, номера счетов, адреса контрагентов.
#   НЕ пушить в публичный репозиторий. sync-to-public.yml удаляет data/import_1c/
#   перед зеркалированием, но data-репо — отдельный репозиторий и не синхронизируется.
#
# Использование:
#   bash scripts/prep-1c-test-data.sh
#
# Предварительные требования:
#   - Локальный каталог backend/data/import_1c/ с актуальными выгрузками
#   - Права на пуш в AlexMobiCraft/FREESPORT-1c-test-data
#   - SSH-ключ или HTTPS-токен с правом repo
#
# Обновление данных:
#   1. Снять свежие выгрузки 1С в backend/data/import_1c/
#   2. Запустить этот скрипт
#   3. CI автоматически подхватит новые данные при следующем прогоне
# ============================================================================

set -euo pipefail

# --- Конфигурация ----------------------------------------------------------
DATA_REPO_URL="github.com/AlexMobiCraft/FREESPORT-1c-test-data.git"
DATA_REPO_NAME="FREESPORT-1c-test-data"

# Каталоги, нужные data_dependent-тестам
REQUIRED_DIRS=(
    "contragents"
    "contragents_pricetype"
    "priceLists"
    "prices"
)

# --- Проверки --------------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel)"
SOURCE_DIR="${REPO_ROOT}/backend/data/import_1c"

if [ ! -d "${SOURCE_DIR}" ]; then
    echo "ОШИБКА: каталог ${SOURCE_DIR} не найден."
    echo "Снимите выгрузки 1С в backend/data/import_1c/ перед запуском."
    exit 1
fi

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "${SOURCE_DIR}/${dir}" ]; then
        echo "ОШИБКА: ${SOURCE_DIR}/${dir} не найден."
        exit 1
    fi
    count=$(find "${SOURCE_DIR}/${dir}" -name '*.xml' | wc -l)
    if [ "${count}" -eq 0 ]; then
        echo "ОШИБКА: в ${SOURCE_DIR}/${dir} нет XML-файлов."
        exit 1
    fi
    echo "  ✓ ${dir}: ${count} XML-файлов"
done

# --- Сборка ----------------------------------------------------------------
STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "${STAGING_DIR}"' EXIT

echo ""
echo "Копирование данных в staging (${STAGING_DIR})..."
for dir in "${REQUIRED_DIRS[@]}"; do
    mkdir -p "${STAGING_DIR}/${dir}"
    cp -r "${SOURCE_DIR}/${dir}/"*.xml "${STAGING_DIR}/${dir}/"
done

# .gitignore внутри data-репо: ничего не игнорировать, всё нужно
cat > "${STAGING_DIR}/.gitignore" <<'GITIGNORE'
# Ничего не игнорировать — все файлы нужны для тестов.
# Этот файл существует, чтобы git не тащил локальные настройки.
*.tmp
.DS_Store
GITIGNORE

cat > "${STAGING_DIR}/README.md" <<'README'
# FREESPORT-1c-test-data

Приватный репозиторий с реальными XML-выгрузками из 1С для data_dependent-тестов.

## Содержание

| Каталог | Файлов | Назначение |
|---------|--------|------------|
| `contragents/` | 7 | test_customer_parser, test_link_then_import, test_import_customers |
| `contragents_pricetype/` | 10 | test_import_role, test_link_applies_role, test_import_customers_price_type, test_customers_price_type_detector, test_customer_processor |
| `priceLists/` | 1 | test_import_opt4_prices |
| `prices/` | 8 | test_import_opt4_prices |

## Обновление

```bash
# Из основного репо FREESPORT
bash scripts/prep-1c-test-data.sh
```

## Безопасность

**ПРИВАТНЫЙ РЕПОЗИТОРИЙ.** Данные содержат персональную информацию
контрагентов (ФИО, ИНН, номера счетов, адреса). Не публиковать.
Основной репозиторий FREESPORT удаляет `data/import_1c/` перед
зеркалированием в публичный репо (sync-to-public.yml).
README

# --- Пуш -------------------------------------------------------------------
echo ""
echo "Инициализация git в staging..."
cd "${STAGING_DIR}"
git init -b main
git config user.name "FREESPORT Data Bot"
git config user.email "bot@optisport.ru"

git add -A
git commit -m "chore: обновление тестовых данных 1С ($(date +'%Y-%m-%d %H:%M'))"

echo ""
echo "Пуш в ${DATA_REPO_URL}..."
git remote add origin "https://${DATA_REPO_URL}"
if ! git push origin main --force 2>&1; then
    echo ""
    echo "ОШИБКА: не удалось запушить в ${DATA_REPO_URL}"
    echo "Возможные причины:"
    echo "  1. Нет прав на AlexMobiCraft/FREESPORT-1c-test-data"
    echo "  2. Репозиторий не создан"
    echo "  3. SSH-ключ/токен не настроен"
    exit 1
fi

echo ""
echo "✅ Данные обновлены в ${DATA_REPO_NAME}"
echo "CI подхватит их при следующем прогоне main.yml."
