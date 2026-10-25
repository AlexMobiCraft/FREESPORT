---
title: 'Отложенное из ревью spec-rich-content-editor: render-тест CmsPage и базовая линия циклов'
type: 'chore'
created: '2026-10-25'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Класс `.rich-content` у CMS-страницы `/[slug]` (`CmsPage`: реквизиты, оферта) не закреплён render-тестом, в отличие от новостей, статей и политики ПДн: если класс откатят, страница потеряет типографику и обтекание картинок, и никто этого не заметит. Кроме того, базовая линия циклов импорта в `.windsurf/rules/gitnexus.md` (правило 3) устарела. В ней нет существующего цикла `backend/apps/users/models.py → staff_roles.py → models.py` (R42.7-D1, импорт `User` под `TYPE_CHECKING`, в рантайме цикла нет), поэтому каждое ревью принимает его за новый.

**Approach:** Добавить в `frontend/src/app/(blue)/[slug]/__tests__/page.test.tsx` render-тесты `CmsPage`: опубликованная страница рендерит заголовок и HTML-контент внутри `.rich-content` с извлечением `<body>`, а несуществующая отдаёт 404-разметку. Обновить базовую линию в правиле 3 до двух циклов с актуальной датой. Закрыть обе записи раздела и R42.7-D1 в `deferred-work.md` пометкой «**Закрыто 2026-10-25**».

</frozen-after-approval>

## Implementation Notes

- `frontend/src/app/(blue)/[slug]/__tests__/page.test.tsx` — блок «CMS-страница: разметка», 5 тестов на `CmsPage`. Модуль грузится через существующий `loadPage()` (сброс `React cache`); `next/link` замокан, как в соседних тестах страниц. После ревью добавлены тесты на пустой контент (404 вместо пустой карточки) и на 5xx (`server_error` пробрасывается).
- Мутация: если заменить `className="rich-content"` на пустой класс, падают оба теста `.rich-content`, остальные зелёные; исходник восстановлен.
- `.windsurf/rules/gitnexus.md`, правило 3 — базовая линия на `a3526e9`: два цикла в том виде, в каком их печатает `check --cycles`.
- `deferred-work.md` — две записи раздела и R42.7-D1 помечены «Закрыто 2026-10-25».
- Проверки: vitest 8/8, `prettier --check`, `eslint --max-warnings=0`, `tsc --noEmit`. `detect-changes` не нашёл задетых проиндексированных символов, `check --cycles` показывает только два базовых цикла.

## Review Triage Log

- Blind Hunter 1, причина цикла неверна: **medium, patch.** `staff_roles.py:69,86,118` импортирует `User` и внутри функций, не только под `TYPE_CHECKING`. Формулировка исправлена в правиле и в пометке о закрытии R42.7-D1.
- 2, формат базовой линии не совпадает с выводом команды: **low, patch.** Записан дословный вывод с `->` и полными путями.
- 3, дата не подтверждена: **false.** `check --cycles` запущен 25.10.2026 на `a3526e9`; коммит добавлен в правило.
- 4, спека не финализирована: **false.** Ревью шло до шага финализации; мутационная проверка выполнена (см. выше).
- 5, нет `baseline_revision` и Review Triage Log: **false.** В шаблоне спеки поля `baseline_revision` нет; лог добавляется на этом шаге.
- 6, не покрыт 5xx у `CmsPage`: **low, patch.** Одна строка `rejects.toThrow('server_error')`.
- 7, не покрыт ответ 200 с пустым контентом: **low, patch.** Добавлен тест на 404-разметку.
- 8, тест извлечения `<body>` проверяет мало: **low, patch.** Добавлена проверка, что в `textContent` нет CSS из `<head>`.
- 9, хлебные крошки не проверены: **low, rejected.** Вне цели (закрепить `.rich-content`); `Breadcrumb` покрыт своими тестами.
- 10, URL запроса к API не закреплён: **low, rejected.** Вне цели; адрес строит одна строка `fetchPage`, его меняют редко.
- 11, дубли `beforeEach`/`afterEach`: **low, rejected.** Косметика, тот же приём, что в первом блоке файла.
