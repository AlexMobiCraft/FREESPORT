---
title: 'UI-навигация и главная страница кабинета руководителя /supervisor/'
type: 'feature'
created: '2026-10-19'
status: 'done'
baseline_commit: '62e240bd643b7a1321e8c426a8f30623bc58e487'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '{project-root}/.windsurf/rules/gitnexus.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В разделе руководителя `/supervisor/` на главной странице показывается промежуточная витрина со списком разделов и моделей вместо рабочей сводки, а при переходе по страницам и в смежные разделы (`/manager/`, `/marketing/`) в левом боковом меню пропадает список разделов руководителя (на главных страницах разделов `#nav-sidebar` вообще отключён шаблоном `admin/index.html`).

**Approach:** Переработать UI и навигацию кабинета руководителя:
1. На главной странице `/supervisor/` сразу открывать раздел «Сводка» (с фильтром периода, таблицами заявок, заказов/выручки и клиентов) и левым боковым меню `#nav-sidebar`; маршрут `/supervisor/summary/` также оставить рабочим для обратной совместимости.
2. Во всех разделах, доступных руководителю (`/supervisor/*`, `/manager/*`, `/marketing/*`, включая главные страницы `/manager/` и `/marketing/`), отображать в левом боковом меню (`#nav-sidebar`) блок «Разделы» (`#supervisor-sections`) с краткими подписями («Сводка», «Журнал действий», «Клиенты и заказы», «Маркетинг») над моделями текущего раздела.
3. Все 4 пункта в блоке «Разделы» всегда остаются в списке, а текущий выбранный раздел выделяется как активный в данный момент (`class="current-model"` на `<tr>` и `aria-current="page"` на `<a>`, в едином стиле с `admin/app_list.html` Django).
4. Ссылку `← Раздел руководителя` (`#supervisor-home-link`) в верхней шапке (`admin/base_site.html`) при нахождении руководителя в `/manager/` и `/marketing/` сохранить (в том числе для мобильных экранов `< 768px`, где боковое меню скрыто).
5. Решение человека после ревью (круг 1): в `/supervisor/*` (сводка, журнал, страницы моделей) в верхней шапке (`admin/base_site.html`, блок `userlinks`) показывать ссылки на остальные разделы руководителя (`#supervisor-header-links`: все пункты «Разделов», кроме текущего выделенного), чтобы на экранах `< 768px` и при свёрнутом боковом меню переход между разделами не пропадал.

## Boundaries & Constraints

**Always:**
- Сохранять существующие правила доступа `StaffSectionAdminSite.has_permission` и `is_supervisor(request)`: блок разделов руководителя и доступ к `/supervisor/` видны только активному сотруднику из группы «Руководители» (не суперпользователю, не менеджеру, не маркетологу).
- Вычислять флаг `current: bool` для пунктов `supervisor_sections` в Python в `StaffSectionAdminSite.each_context` по точным правилам (не через `in request.path` в шаблоне, иначе `/supervisor/` подсвечивал бы «Сводку» на всех вложенных URL):
  - «Сводка» (`url = reverse("supervisor:index")`): `self.name == "supervisor" and request.path in (reverse("supervisor:index"), reverse("supervisor:summary"))`
  - «Журнал действий» (`url = reverse("supervisor:journal")`): `self.name == "supervisor" and request.path == reverse("supervisor:journal")`
  - «Клиенты и заказы» (`url = reverse("manager:index")`): `self.name == "manager"`
  - «Маркетинг» (`url = reverse("marketing:index")`): `self.name == "marketing"`
- На главных страницах `/manager/` и `/marketing/` включать `{% block nav-sidebar %}` только при наличии `supervisor_sections` в контексте (`{% if supervisor_sections %}{% include "admin/nav_sidebar.html" %}{% endif %}`), чтобы у обычного менеджера и маркетолога главная страница их раздела не дублировала модели.
- В `SupervisorAdminSite.index` передавать в контекст `app_list: context["available_apps"]` (без второго вызова `get_app_list`), чтобы сохранить совместимость контекста главной страницы.
- Соблюдать NFR по числу SQL-запросов (`TestQueryCount` в `test_supervisor_summary.py`, `test_supervisor_section.py`, `test_staff_journal.py`): формирование меню разделов в `each_context` не должно выполнять дополнительных SQL-запросов сверх кэшированного `is_supervisor(request)`.
- Все пользовательские данные в шаблонах выводить через автоэкранирование Django без `|safe`.
- Сохранять совместимость с `nav_sidebar.js` (каждая строка в `#supervisor-sections` использует `<th scope="row"><a ...>...</a></th><td></td>`).

**Never:**
- Не менять фронтенд Next.js (`frontend/`), REST API, `openapi.yaml` или модели БД.
- Не показывать ссылки на `/supervisor/` или блок `#supervisor-sections` обычным менеджерам, маркетологам и суперпользователю в `/admin/`.
- Не включать блок «Последние действия» (`sidebar`) на страницах сотрудников, чтобы не генерировать ссылки на закрытую `/admin/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Вход руководителя на `/supervisor/` или `/supervisor/summary/` | `GET /supervisor/` или `GET /supervisor/summary/` (в т.ч. с `?date_from=...&date_to=...`) | Рендерится сводка (период, заявки, заказы и выручка, клиенты) и левое меню `#nav-sidebar`; в блоке «Разделы» все 4 пункта, пункт «Сводка» выделен как активный (`current-model`, `aria-current="page"`) | Невалидный период — показ ошибки над формой и расчёт за период по умолчанию («Этот месяц») |
| Руководитель на странице «Журнал действий» | `GET /supervisor/journal/` | В левом меню в блоке «Разделы» все 4 пункта, пункт «Журнал действий» выделен как активный (`current-model`, `aria-current="page"`), ниже — модели `/supervisor/` | N/A |
| Руководитель на страницах моделей `/supervisor/*` | `GET /supervisor/users/user/`, `/supervisor/common/managerroutingrule/` и др. | В левом меню блок «Разделы» (все 4 пункта без выделения `current-model`) + модели `/supervisor/`, где текущая модель выделена штатно | N/A |
| Руководитель в `/manager/*` или `/marketing/*` | `GET /manager/`, `/manager/users/user/`, `/marketing/`, `/marketing/banners/banner/` и др. | На всех страницах (включая главные `/manager/` и `/marketing/`) у руководителя рендерится `#nav-sidebar` с блоком «Разделы», где «Клиенты и заказы» (в `/manager/*`) или «Маркетинг» (в `/marketing/*`) выделен как активный; в шапке есть `#supervisor-home-link` | Менеджер и маркетолог не видят `#supervisor-sections` и `#supervisor-home-link`, а на главных `/manager/` и `/marketing/` у них нет `#nav-sidebar` |
| Руководитель в `/supervisor/*` при скрытом или свёрнутом боковом меню | `GET /supervisor/`, `/supervisor/journal/`, `/supervisor/users/user/` | В шапке есть `#supervisor-header-links` со ссылками на все разделы, кроме текущего (на моделях `/supervisor/*` — на все 4) | Менеджер, маркетолог, суперпользователь и руководитель в `/manager/`, `/marketing/` блока не получают (там остаётся `#supervisor-home-link`) |
| Неавторизованный / чужая роль на `/supervisor/` | Менеджер, маркетолог, суперпользователь, аноним | `302` на `/supervisor/login/?next=/supervisor/` | Штатный редирект `admin_view` |

</frozen-after-approval>

## Code Map

- `backend/freesport/admin_site.py` -- `StaffSectionAdminSite.each_context` и `SupervisorAdminSite` (`index`, `summary_view`, `journal_view`, `_supervisor_sections`): формирование `supervisor_sections` с флагом `current` для руководителя во всех трёх сайтах разделов и рендер сводки в `SupervisorAdminSite.index` и `summary_view`.
- `backend/templates/admin/nav_sidebar.html` -- шаблон бокового меню Django Admin: вывод блока `<div class="app-supervisor-sections module" id="supervisor-sections">` над фильтром `#nav-filter` и `admin/app_list.html`, когда в контексте есть `supervisor_sections`.
- `backend/templates/admin/supervisor/summary.html` -- шаблон сводки: используется для `/supervisor/` и `/supervisor/summary/`, сохраняет блок `nav-sidebar` из `base.html`.
- `backend/templates/admin/supervisor/index.html` -- удаляется или заменяется на `summary.html` (так как `SupervisorAdminSite.index` рендерит `admin/supervisor/summary.html`).
- `backend/templates/admin/manager/index.html` и `backend/templates/admin/marketing/index.html` -- условное включение блока `nav-sidebar` (`{% block nav-sidebar %}{% if supervisor_sections %}{% include "admin/nav_sidebar.html" %}{% endif %}{% endblock %}`).
- `backend/templates/admin/base_site.html` -- сохраняет ссылку `#supervisor-home-link` в `userlinks` и добавляет `#supervisor-header-links` (ключ контекста `supervisor_header_links`, кладёт `each_context` только на сайте `supervisor`).
- `backend/tests/integration/test_supervisor_section.py`, `backend/tests/integration/test_supervisor_summary.py`, `backend/tests/integration/test_staff_journal.py` -- обновление и добавление тестов навигации руководителя и главной `/supervisor/`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/freesport/admin_site.py` -- В `StaffSectionAdminSite.each_context` формировать для руководителя список `supervisor_sections` (4 пункта: «Сводка» `/supervisor/`, «Журнал действий» `/supervisor/journal/`, «Клиенты и заказы» `/manager/`, «Маркетинг» `/marketing/`) с вычислением `current: bool`; в `SupervisorAdminSite.index` и `summary_view` рендерить сводку с передачей `app_list: context["available_apps"]` -- Делает «Сводку» главной страницей `/supervisor/` и передаёт структуру меню разделов во все шаблоны без лишних запросов к БД.
- [x] `backend/templates/admin/nav_sidebar.html` -- Создать шаблон бокового меню с блоком `#supervisor-sections` (`<table><caption>Разделы</caption>...`), помечающим активный пункт классом `current-model` на `<tr>` и `aria-current="page"` на `<a>` -- Обеспечивает сквозное левое меню разделов с подсветкой текущего раздела.
- [x] `backend/templates/admin/manager/index.html` -- В `backend/templates/admin/manager/index.html` и `backend/templates/admin/marketing/index.html` включить `{% block nav-sidebar %}` при наличии `supervisor_sections`, а неиспользуемый `backend/templates/admin/supervisor/index.html` удалить -- Включает левое меню для руководителя на главных страницах разделов, где стандартный `admin/index.html` его скрывал.
- [x] `backend/templates/admin/base_site.html` -- В `each_context` на сайте `supervisor` класть `supervisor_header_links` (пункты `supervisor_sections` без `current`), в `userlinks` выводить их как `<span id="supervisor-header-links">` ссылок через « / » -- Сохраняет переходы между разделами руководителя на узких экранах и при свёрнутом меню (решение человека, круг 1).
- [x] `backend/tests/integration/test_supervisor_section.py` -- Обновить и дополнить тесты в `test_supervisor_section.py`, `test_supervisor_summary.py` и `test_staff_journal.py` под новую главную страницу `/supervisor/` и сквозной блок `#supervisor-sections` в левом меню с выделением активного раздела -- Проверяет все сценарии матрицы и соблюдение NFR по числу SQL-запросов.

**Acceptance Criteria:**
- Given авторизованный руководитель, when он открывает `/supervisor/`, then сразу открывается раздел «Сводка» (с фильтром периода, таблицами заявок, заказов/выручки и клиентов) и левым меню `#nav-sidebar`.
- Given авторизованный руководитель, when он находится в «Сводке» (`/supervisor/` или `/supervisor/summary/`), «Журнале действий» (`/supervisor/journal/`), «Клиентах и заказах» (`/manager/*`) или «Маркетинге» (`/marketing/*`), then в левом меню `#nav-sidebar` отображается блок `#supervisor-sections` со всеми 4 разделами, а текущий раздел выделен классом `current-model` и `aria-current="page"`.
- Given авторизованный руководитель, when он находится на странице модели внутри `/supervisor/*` (например `/supervisor/users/user/`), then в левом меню отображаются все 4 раздела (ни один из них не помечен `current-model`) и список моделей `/supervisor/`, в котором активная модель выделена штатно.
- Given авторизованный руководитель, when он находится в `/supervisor/*`, then в шапке есть `#supervisor-header-links` со ссылками на разделы руководителя, кроме выделенного текущего.
- Given менеджер, маркетолог или суперпользователь, when он открывает `/manager/*`, `/marketing/*` или `/admin/*`, then блок `#supervisor-sections`, `#supervisor-header-links` и ссылки на `/supervisor/` в HTML отсутствуют.

## Implementation Notes

- `admin/nav_sidebar.html` создан как копия шаблона Django 5.2 плюс блок «Разделы»; при обновлении Django разметку сверить с оригиналом.
- Сверх списка файлов добавлен `backend/templates/admin/app_index.html` (надстройка над Django): у страниц приложений (`/supervisor/users/`, `/manager/users/`) блок `nav-sidebar` пуст, и руководитель терял «Разделы» при клике по заголовку блока в меню. Включается только при `supervisor_sections`.
- `SupervisorAdminSite.index_template` удалён вместе с `admin/supervisor/index.html`: `index` и `summary_view` делят `_summary_response`.

## Spec Change Log

## Review Triage Log

- Круг 1, intent_gap: на экранах `< 768px` и при свёрнутом меню из `/supervisor/*` нет ссылок на другие разделы. Решено человеком: ссылки в шапке (пункт 5 Approach).
- Круг 1, patch (применить при реализации): на `/supervisor/` убрать из хлебных крошек «› Сводка»; в тесте главной проверять непустой `app_list` вместо сравнения с самим собой; тест равенства числа SQL-запросов у `/supervisor/` и `/supervisor/summary/`.
- Круг 1, reject: фильтр меню скрывает «Разделы» (совместимость с `nav_sidebar.js` — требование), короткие подписи (заданы спекой), перевод строк, дубли списков в тестах, пустой `available_apps`.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs tests/unit/test_supervisor_admin_site.py tests/unit/test_supervisor_summary.py tests/integration/test_supervisor_section.py tests/integration/test_supervisor_summary.py tests/integration/test_staff_journal.py` -- expected: все тесты проходят.

## Suggested Review Order

**Меню разделов: откуда берётся и как выделяется текущий**

- Точка входа: `each_context` кладёт `supervisor_sections` руководителю во все три сайта, без лишних запросов.
  [`admin_site.py:68`](../../backend/freesport/admin_site.py#L68)

- `current` считается по сайту и точному пути, а не по префиксу в шаблоне.
  [`admin_site.py:87`](../../backend/freesport/admin_site.py#L87)

- Блок «Разделы» над фильтром; строки в стиле моделей, совместимо с `nav_sidebar.js`.
  [`nav_sidebar.html:14`](../../backend/templates/admin/nav_sidebar.html#L14)

**Главная `/supervisor/` — сводка**

- `index` и `summary_view` делят один рендер; `app_list` ставится до `extra_context`.
  [`admin_site.py:237`](../../backend/freesport/admin_site.py#L237)

- Хлебные крошки остались только у `/supervisor/summary/`, главная не ссылается на себя.
  [`summary.html:15`](../../backend/templates/admin/supervisor/summary.html#L15)

**Меню там, где Django его отключал**

- Главные `/manager/` и `/marketing/`: меню включается только при `supervisor_sections`.
  [`manager/index.html:12`](../../backend/templates/admin/manager/index.html#L12)
  [`marketing/index.html:11`](../../backend/templates/admin/marketing/index.html#L11)

- Страницы приложений (`/supervisor/users/`): та же надстройка над `admin/app_index.html`.
  [`app_index.html:9`](../../backend/templates/admin/app_index.html#L9)

**Шапка для узких экранов (решение круга 1)**

- Ссылки на остальные разделы в `/supervisor/*`, пока боковое меню скрыто или свёрнуто.
  [`base_site.html:18`](../../backend/templates/admin/base_site.html#L18)

**Тесты**

- Матрица «страница → выделенный раздел», шапка и отсутствие блока у других ролей.
  [`test_supervisor_section.py:354`](../../backend/tests/integration/test_supervisor_section.py#L354)

- Главная стоит столько же запросов, сколько `/supervisor/summary/`.
  [`test_supervisor_summary.py:687`](../../backend/tests/integration/test_supervisor_summary.py#L687)
