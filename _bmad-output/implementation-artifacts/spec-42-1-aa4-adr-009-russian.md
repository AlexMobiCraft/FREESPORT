---
title: 'Story 42.1, замечание ревью AA4 — пункт ADR-009 на русском'
type: 'chore'
created: '2026-10-09'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
story_key: '42-1-staff-roles-and-service-access-lockdown'
baseline_commit: '9f263794b06a1ca9dac909e4123ace765d43f8d2'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/Story/42-1-staff-roles-and-service-access-lockdown.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В стори 42.1 изменённый пункт «Permission Check» в `docs/decisions/ADR-009-csrf-exemption-1c-protocol.md:26` написан на английском, а документацию проекта положено вести на русском (замечание ревью AA4, единственный открытый пункт стори).

**Approach:** Перевести на русский только этот пункт, не меняя смысла (доступ к обмену — только по праву `can_exchange_1c`, суперпользователь проходит через `has_perm`, `is_staff` доступа не даёт, эпик 42), остальной ADR не переписывать. Отметить AA4 выполненным в файле стори.

</frozen-after-approval>

## Implementation Notes

- `docs/decisions/ADR-009-csrf-exemption-1c-protocol.md` — переведён только пункт «Permission Check» → «Проверка прав». Смысл сверен с `backend/apps/integrations/onec_exchange/permissions.py`. Остальной ADR не переводился: AA4 ограничивает правку этим пунктом («без переписывания остального ADR»). Поэтому в файле теперь смешаны языки.
- Файл стори 42.1: пункт AA4 отмечен выполненным. `sprint-status.yaml` не менялся: стори уже в `in-progress`, а для `done` нужно решение владельца.
- Работа идёт в ветке `feature/42-1-review-aa4-adr-russian` от `develop` (`9f263794`).


## Review Triage Log

Слой Blind Hunter (N = 3, найдено 8 замечаний).

- Противоречие в стори: AA4 отмечен `[x]`, а «Решение владельца» говорит, что замечание открыто — low, patch: в стори добавлено «Дополнение 09.10.2026».
- «Единственный открытый пункт» при неотмеченных Task 0–8 — low, defer: отмечаю, что чекбоксы не проставлялись ещё до этого запуска; фраза спеки относится к замечаниям ревью, а не к задачам. Записано в `deferred-work.md`.
- Статус спеки `in-progress` и нет раздела проверки — false: статус переводится в `done` на этом шаге; шаблон oneshot убирает разделы Verification и Tasks.
- В ADR смешаны языки, нет задачи на перевод остального, заметка неверно толкует AA4 — low: формулировка заметки исправлена. Перевод всего ADR отклонён: правку пунктом ограничил сам AA4, и решение владельца прямо запрещает переписывать остальное.
- Нет слова «активный» и полного имени права — low, patch: в ADR теперь «активный суперпользователь» и `integrations.can_exchange_1c`.
- «Must» передан как описание, а не требование — low, patch: «должен по-прежнему проходить».
- Не проверен `docs/integrations/1c/transport-layer.md:27-31` — false: сам рецензент пишет, что противоречия нет; документ вне рамок AA4.
- Ссылка на спеку без пути и без ветки — low, patch: в стори указаны полный путь и ветка.
