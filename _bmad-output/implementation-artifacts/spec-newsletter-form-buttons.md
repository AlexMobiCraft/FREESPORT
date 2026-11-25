---
title: 'Кнопки «Сделать рассылку» и «Отправить тестовое письмо мне» на форме новости и статьи'
type: 'feature'
created: '2026-11-25'
status: 'done'
baseline_commit: '1326cf59aa864fb2c76ed40104d2ef5a7b66db27'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-newsletter-news-blog-mailing.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Рассылку и тестовое письмо (спека `spec-newsletter-news-blog-mailing`) можно запустить только действиями в списке новостей: выбрать галочку, найти действие в выпадающем меню. На форме самой новости, где сотрудник её пишет, этих кнопок нет.

**Approach:** На форме новости и статьи блога в `/marketing/` и `/admin/` добавить две кнопки: «Сохранить и сделать рассылку» и «Сохранить и отправить тестовое письмо на мой e-mail». Кнопки вызывают готовые `start_campaign` и `send_test`, новой логики отправки нет. Доступны тем, у кого есть право изменять материал: «Руководители» и «Маркетинг» в `/marketing/`, суперпользователь в `/admin/`.

**Решения владельца (25.11.2026):**
- **Формы:** новости и статьи блога одинаково (общий `NewsletterMailingAdminMixin`). Действия в списках остаются.
- **Сохранение:** кнопки есть на форме «Добавить» и на форме правки. Сначала материал сохраняется (как «Сохранить», со штатным сообщением), затем выполняется действие. Ошибка валидации формы — действие не выполняется, форма показывает ошибки.
- **Тест:** уходит сразу, в том числе по неопубликованному материалу (черновик проверяют первым), затем возврат на форму правки.
- **Рассылка:** после сохранения редирект на GET-страницу подтверждения «Отправить N подписчикам?» (повтор запроса по F5 ничего не дублирует). «Отмена» возвращает на форму материала, «Да» запускает рассылку и ведёт на список с сообщением об успехе (как у действия списка).

## Boundaries & Constraints

**Always:**
- Правила рассылки из `spec-newsletter-news-blog-mailing` не меняются: суточный потолок, только опубликованное, `AuditLog` `newsletter_send`, тестовое письмо без кампании и без `List-Unsubscribe`.
- Кнопки видны и действуют только при `has_change_permission(request, obj)`. Проверка — и в шаблоне, и внутри обработчика: POST с именем кнопки от роли без `change` материал сохраняет (если разрешено `add`), действие не выполняет.
- Кнопки стоят после штатной «Сохранить» (`{{ block.super }}`): Enter в поле формы по-прежнему сохраняет без отправки.
- Сбой `send_test` не откатывает сохранение материала. `NewsletterCampaignError` (пустой email сотрудника и т. п.) показывает свой текст как есть, как у действия списка. Любое другое исключение и `status != "sent"` — лог `logger.exception` / `logger.error`, сообщение `TEST_FAILED_MESSAGE`.
- Редирект после действия сохраняет `_changelist_filters`.
- Действия в списке («Разослать подписчикам», «Отправить тест мне») работают как раньше; их страница подтверждения и «Отмена» в список не меняются.
- Перед правкой символа — `npx gitnexus impact`; pytest — последовательно.

**Never:** новая логика отправки в обход `start_campaign`/`send_test`; рассылка без страницы подтверждения; подтверждение ответом на POST формы; миграции.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Тест с формы | материал (в т.ч. новый или черновик), у сотрудника есть email | материал сохранён, письмо на email сотрудника, сообщение «Тестовое письмо отправлено на …», форма правки | сбой транспорта или любое исключение → `TEST_FAILED_MESSAGE`, материал остаётся сохранённым |
| Тест, у сотрудника пустой email | любой материал, `user.email` пуст | материал сохранён, сообщение `NO_EMAIL_MESSAGE` (как у действия списка), форма правки | не `TEST_FAILED_MESSAGE`: «ошибка почтового сервера» вводила бы в заблуждение |
| Рассылка с формы | опубликованный материал после сохранения | редирект на страницу «Отправить N подписчикам?» (GET), «Да» — рассылка запущена, список | потолок, «уже отправлено всем», сбой Redis — те же сообщения, возврат на форму |
| Рассылка по черновику | `is_published=False` или дата в будущем | материал сохранён, кампании нет, `NOT_PUBLISHED_MESSAGE`, форма правки | — |
| «Отмена» | страница подтверждения с формы | ничего не отправлено, форма материала | — |
| Ошибка валидации формы | пустой заголовок и т.п. | форма с ошибками, действие не выполняется | стандартный вывод ошибок админки |
| Повтор GET страницы подтверждения (F5) | — | тот же экран, дублей нет | — |
| Роль «только просмотр» | открывает форму | кнопок нет | POST — 403 (штатно) |
| Роль с `add`, без `change` | форма «Добавить» | кнопок нет; POST с именем кнопки сохраняет материал, действие не выполняется | — |
| Суперпользователь в `/marketing/` | — | 302 на логин (штатно), кнопки — только в `/admin/` | — |

</frozen-after-approval>

## Code Map

- `backend/apps/common/admin.py:375-490` -- `NewsletterMailingAdminMixin`: `send_newsletter`, `send_newsletter_test`, `_start_newsletter`. Логику по объекту вынести в общие методы (тест по объекту; подтверждение по объекту → `TemplateResponse | None`) и вызывать и из действий, и из новых мест. Добавить `change_form_template`, `response_add`/`response_change` (имена кнопок в POST: `_newsletter_send`, `_newsletter_test`; штатный `super()` отрабатывает первым, сообщение о сохранении остаётся) и `get_urls` с `<path:object_id>/newsletter/confirm/` **до** `super().get_urls()` — иначе catch-all `<path:object_id>/` перехватит путь
- `backend/apps/common/admin.py:38-49` -- импорты из `services.newsletter_campaign`: добавить `NO_EMAIL_MESSAGE` (сейчас не импортирован; нужен только для тестов и сверки текста, в коде — `str(error)`); `reverse` для маршрута подтверждения — как `RichContentAdminMixin`: `f"{self.admin_site.name}:<app>_<model>_newsletter_confirm"`. GitNexus: `impact NewsletterMailingAdminMixin` — MEDIUM, 5 прямых, процессов нет
- `backend/apps/common/admin.py:494,578` -- `NewsAdmin`, `BlogPostAdmin` (наследуют миксин); `marketing_admin.py` наследует их
- `backend/apps/common/rich_editor.py:215` -- `RichContentAdminMixin` стоит в MRO после миксина рассылки и тоже добавляет `get_urls` (`upload-image/`); не ломать
- `backend/templates/admin/common/newsletter_send_confirmation.html` -- `<form action="">` и «Отмена» в список; ввести `form_action` (список) и `cancel_url` (форма материала или список) в контексте
- `backend/templates/admin/common/managerroutingrule/change_list.html` -- образец шаблона-расширения админки
- `backend/apps/common/tests/test_newsletter_admin.py` -- фикстуры (`as_marketer`, `make_staff_member`), `TestActionsAndRights`, `TestConfirmation`, `TestTestLetter`; не ломать, расширять

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/common/admin.py` -- общие методы по объекту; `response_add`/`response_change`; GET-маршрут и представление подтверждения (`admin_view`, право `change`, 404 на чужой pk, те же проверки публикации, потолка и числа получателей, что у действия); вокруг `send_test` — `except NewsletterCampaignError` первым (текст как есть), затем `except Exception`; сам вызов внутри вложенного `transaction.atomic()` (savepoint): `response_add`/`response_change` выполняются внутри `atomic` формы (`changeform_view`), и ошибка БД без savepoint отравит транзакцию и потеряет сохранение материала. Редирект с формы на страницу подтверждения несёт `_changelist_filters` (`add_preserved_filters`); «Да» ведёт в список с фильтрами, «Отмена» — на форму с фильтрами
- [x] `backend/templates/admin/common/newsletter_change_form.html` -- расширяет `admin/change_form.html`; переопределяет `submit_buttons_bottom`: `{{ block.super }}` (штатный ряд, «Сохранить» первая в DOM), затем **второй** `<div class="submit-row">` с двумя кнопками при праве `change`. Внутрь штатного ряда кнопки не попадают: `submit-row` — блок inclusion-тега `submit_line.html`, из дочернего шаблона он недоступен
- [x] `backend/templates/admin/common/newsletter_send_confirmation.html` -- `form_action`, `cancel_url`
- [x] `backend/apps/common/tests/test_newsletter_admin.py` -- все строки матрицы для новости и статьи в `/marketing/` и `/admin/`; порядок кнопок в HTML (штатная «Сохранить» раньше наших, наши — во втором `submit-row`); `csrfmiddlewaretoken` на странице подтверждения; повторный GET; тест после сбоя `send_test` с `ValueError` и отдельно с `DatabaseError` (материал сохранён, дальнейшие запросы к БД работают); пустой email → `NO_EMAIL_MESSAGE`, не `TEST_FAILED_MESSAGE`; `_changelist_filters` проходит форма → подтверждение → список и «Отмена» → форма

**Acceptance Criteria:**
- Given «Маркетинг» или «Руководители» на форме новости или статьи в `/marketing/`, либо суперпользователь в `/admin/`, when открыта форма, then обе кнопки видны после «Сохранить».
- Given роль «только просмотр», when открыта форма, then кнопок нет.
- Given заполненная форма «Добавить» и email сотрудника, when нажата «Сохранить и отправить тестовое письмо», then материал создан, письмо пришло только сотруднику без `List-Unsubscribe`, `NewsletterCampaign`/`NewsletterDelivery` не созданы.
- Given опубликованный материал, when нажата «Сохранить и сделать рассылку» и затем «Да», then запущена кампания, записан `AuditLog` `newsletter_send`, открыт список с сообщением об успехе.
- Given страница подтверждения с формы, when нажата «Отмена», then кампании нет, открыта форма материала.
- Given у сотрудника пустой email, when нажата «Сохранить и отправить тестовое письмо», then материал сохранён, показано `NO_EMAIL_MESSAGE`, письмо не отправлялось.
- Given форма открыта из отфильтрованного списка, when выполнено любое из двух действий и затем «Да» или «Отмена», then фильтры списка не потеряны.

## Implementation Notes

- **Почему подтверждение — отдельный GET-запрос.** `start_campaign` и явный `.delay()` выполняются в запросе «Да», вне `transaction.atomic` формы. Если вызвать `_start_newsletter` прямо из `response_change`, `.delay()` уйдёт до коммита сохранения материала: тот же класс дефекта, что в потере писем о заказах. Не «упрощать» до вызова из `response_change`.
- **Два ряда кнопок — осознанно.** Второй `submit-row` под штатным (решение владельца 25.11.2026). Единый ряд потребовал бы своего `submit_line.html` и задел бы чужие модели.
- **Порядок `except` в тесте с формы** повторяет `send_newsletter_test` (`admin.py:481-490`): `NewsletterCampaignError` — текст как есть, затем общий случай.

## Spec Change Log

- **25.11.2026, по слову владельца (frozen):** (1) правило Boundaries про сбой `send_test` — `NewsletterCampaignError` показывается как есть, `TEST_FAILED_MESSAGE` только для остальных сбоев; (2) в матрицу добавлена строка «Тест, у сотрудника пустой email». Причина: `send_test` бросает `NewsletterCampaignError(NO_EMAIL_MESSAGE)` при пустом email (`services/newsletter_campaign.py:206`), общий `except Exception` выдал бы «ошибка почтового сервера». Остальное — в Tasks, Notes и AC, frozen не тронут.

## Review Triage Log

**Ревью спеки 25.11.2026 (субагент; Django-утверждения не сверены с исходниками — проверить при реализации)**

| # | Находка | Вердикт | Что сделано |
|---|---|---|---|
| 1 | В Code Map ссылка на «вариант A» без варианта B | low | описан механизм кнопок |
| 2 | Исключение `send_test` внутри `transaction.atomic` формы откатит сохранение и потеряет текст | medium | `try/except Exception` вокруг теста, строка матрицы |
| 3 | Подтверждение ответом на POST: F5 повторяет сохранение, дубль на «Добавить» | medium | решение владельца: GET-страница после редиректа |
| 4 | Один шаблон подтверждения на два входа, `action=""` и «Отмена» в список | medium | `form_action`, `cancel_url` |
| 5 | Роль с `add` без `change` | medium | проверка в обработчике, строка матрицы |
| 6 | Суперпользователь в `/marketing/` получает 302; критерий «менеджер» не проверялся | low | роль «только просмотр», строка матрицы |
| 7 | Черновик: тест должен уходить, рассылка — отказ | low | зафиксировано в решениях и матрице |
| 8 | Enter срабатывает по первой submit-кнопке | low | кнопки после «Сохранить», тест порядка |

**Party-mode 25.11.2026 (сверка с Django 5.2.7 и `newsletter_campaign.py`)**

| # | Находка | Вердикт | Что сделано |
|---|---|---|---|
| 9 | `submit-row` — блок внутри inclusion-тега `submit_line.html`; `{{ block.super }}` отдаёт весь `<div class="submit-row">`, кнопки «в submit-row» не встанут | medium | второй ряд (решение владельца), Task 2 переписан |
| 10 | `response_add`/`response_change` внутри `atomic` (`changeform_view`): `except Exception` не спасает от ошибки БД | medium | savepoint вокруг `send_test`, тест с `DatabaseError` |
| 11 | Пустой email → `NewsletterCampaignError`, общий `except` показал бы «ошибка почтового сервера» | medium | frozen: правило и строка матрицы, AC, тест |
| 12 | `_changelist_filters` не упомянут для редиректа форма → подтверждение | low | Task 1, AC, тест |
| 13 | Manual check «двойной клик» без ожидаемого результата | low | см. Verification |
| 14 | Нужна фраза, почему подтверждение вне `atomic` формы | low | Implementation Notes |

**Ревью реализации 25.11.2026 (Blind Hunter, Edge Case Hunter, Verification Gap, Graph Impact)**

| # | Находка | Вердикт | Что сделано |
|---|---|---|---|
| 15 | VG: тест «add без change» для `_newsletter_send` проходит и без проверки `has_change_permission` в `_newsletter_button_response` (редирект на confirm остаётся 302, кампании нет) | low, patch | assert на `Location` без `/newsletter/confirm/` |
| 16 | BH: `caplog`-проверка `exc_info` в тесте `ValueError` принимает любую запись | low, patch | требовать запись логгера `apps.common.admin` |
| 17 | BH: ветка `_popup` в `_newsletter_button_response` без теста | low, patch | тест POST с `_popup=1` |
| 18 | BH/EC: SMTP внутри `atomic` формы держит блокировку и откатит сохранение при убитом воркере | false | у `SmtpMarketingTransport` есть `timeout=SMTP_TIMEOUT_SECONDS`; вызов внутри savepoint — требование спеки (Task 1) |
| 19 | BH: тест `DatabaseError` может не доказывать отравленную транзакцию | false | исполнитель убрал savepoint: 4 теста упали с `InternalError: current transaction is aborted` |
| 20 | BH: имена кнопок дублируются в шаблоне и миксине | low, rejected | вред — только при переименовании, тесты ловят; исправление усложняет контекст |
| 21 | BH: объектная проверка `has_change_permission` не покрыта | low, rejected | то же, что №15 |
| 22 | BH: лишний флаг `from_list`, структура `_send_test_letter` | low, rejected | стиль без названного вреда |
| 23 | BH/EC: HEAD/OPTIONS на странице подтверждения дают 405 | low, rejected | страницу открывает человек из админки; исправление — ветвление ради редкого случая |
| 24 | BH: нет CSS и визуальной проверки второго ряда кнопок | low, rejected | косметика; ручная проверка в Verification остаётся за владельцем |
| 25 | BH: тест-письмо не пишется в `AuditLog` | false | спека требует журнал только для `newsletter_send`; у действия списка журнала тоже нет |
| 26 | EC: исключение после приёма письма SMTP покажет `TEST_FAILED_MESSAGE` | low, rejected | после `send_test` в savepoint нет кода, способного бросить |
| 27 | EC: POST с обеими кнопками выполнит только тест | low, rejected | браузер шлёт одну кнопку; только вручную составленный запрос |
| 28 | EC: 404 против 403 раскрывает существование pk | false | роль «только просмотр» и так видит все материалы в списке |
| 29 | EC: POST на confirm без `post=yes` запускает рассылку | false | по спеке POST на этот URL и есть «Да»; защищён CSRF и правом `change` |
| 30 | EC: пустой `cancel_url` | false | оба вызывающих передают значение |
| 31 | GI: слой не выполнен, индекс `stale` (правки не закоммичены) | false | после `analyze --force` слой повторён: находок нет; `_start_newsletter` LOW (2 вызывающих, оба учтены), миксин MEDIUM, новых циклов импорта нет |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/common/tests/test_newsletter_admin.py` -- expected: зелёно
- навык `backend-lint` -- expected: black/isort/flake8 чисто

**Manual checks:**
- Стенд с Mailhog (`http://localhost:8025`): тест с формы «Добавить» и формы правки, рассылка по новости и статье блога, F5 на странице подтверждения, «Отмена», открытие формы из отфильтрованного списка. Двойной клик по кнопке: на «Добавить» второй POST — штатное поведение админки (дубль или ошибка уникальности slug), записать фактический результат; на форме правки тест уходит дважды, рассылка — одним экраном подтверждения.
