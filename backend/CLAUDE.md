# Backend — CLAUDE.md

## Изоляция тестов (специфика проекта)

Конфликты уникальности между тестами предотвращают:

- **Автоочистка БД:** autouse-фикстура `clear_db_before_test` в `backend/tests/conftest.py` удаляет данные через `DELETE` перед каждым тестом. `TRUNCATE ... CASCADE` — только в явной фикстуре `truncate_db`.
- **Уникальные данные:** `get_unique_suffix()` (timestamp + счетчик + UUID).
- **Factory Boy:** `LazyFunction` вместо статических значений и `Sequence`.
- **Тестовая БД строится с миграциями:** флагов `--nomigrations` / `--create-db` нет ни в `pytest.ini`, ни в `docker-compose.test.yml`, поэтому данные data-миграций в тестовой БД присутствуют.

Маркеры и покрытие: `backend/docs/testing-standards.md`.
