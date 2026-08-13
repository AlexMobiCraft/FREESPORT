---
title: 'Оповещение о падении nightly perf-тестов через GitHub Issue'
type: 'chore'
created: '2026-08-13'
status: 'done'
baseline_commit: '1b675f9ac57677018d7fe52c4bc2e664623767fa'
review_loop_iteration: 2
context:
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `performance-tests.yml` — единственное место исполнения `performance`- и `slow`-тестов — не имеет никакого оповещения о падении. Правки 2026-08-06 подняли ставку, выведя `slow` из всех PR-гейтов сюда же, а защита веток фактически отсутствует (`project_branch_protection_absent`), поэтому красный nightly не заметит никто.

**Approach:** Два шага на `actions/github-script@v7`: при падении — дописать комментарий в открытый issue с меткой `nightly-failure` либо создать его, если такого нет; при успехе — закрыть. Один живой issue на одну непрерывную полосу падений, а не по issue за ночь. Сигнал покрывает **любое** падение прогона: и падение тестов, и сбой окружения до них (`pip install`, postgres, `migrate`) — различаются они текстом сообщения, а не наличием сигнала.

## Boundaries & Constraints

**Always:**
- Оповещение только для прогонов на ветке по умолчанию (`develop`); `workflow_dispatch` с feature-ветки issue не создаёт.
- Сигнал даёт **любое** падение прогона, а не только падение шага тестов. Причина различается по `steps.tests.outcome` и уходит в текст сообщения: `failure` → «тесты падают», иначе → «до тестов дело не дошло, сломано окружение». Заголовок issue нейтрален к причине — иначе первый по времени повод навсегда определил бы название задачи, в которую потом дописываются падения другого рода.
- Отмена прогона (ручная или по `timeout-minutes`) сигнала не даёт и не должна: при отмене `failure()` ложно, а отличить намеренную отмену человеком от таймаута из выражения `if` нечем. Ограничение фиксируется в документации, а не обходится через `always()`.
- Поиск открытого issue — по метке `nightly-failure`, не по заголовку.
- В теле issue и комментариев только: имя workflow, ссылка на прогон, SHA, дата. Репозиторий `AlexMobiCraft/FREESPORT` публичный.
- Job получает `permissions` с `contents: read` **и** `issues: write`: блока сейчас нет вовсе, и один `issues: write` обнулил бы права на checkout.
- Шаг закрытия issue — `continue-on-error: true`: сбой уборки не красит зелёный прогон в красный.

**Ask First:**
- Канал оповещения за пределами GitHub Issue (Telegram, email) — требует секрета, которого в репозитории нет.
- Изменение фильтра тестов nightly (`-m "performance or slow"`).

**Never:**
- Не менять шаги установки, миграций и запуска pytest.
- Не заводить метку отдельным шагом — GitHub создаёт её сам при `issues.create`.
- Не трогать другие workflow: у них есть PR-сигнал, у nightly его нет — в этом и причина правки.
- Не звать `issues.create` без предварительного поиска.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Первое падение тестов | Прогон на `develop` упал на pytest, открытых issue с меткой нет | Создан issue с меткой `nightly-failure`, причина — «тесты падают»: ссылка на прогон, SHA, метка времени | N/A |
| Сбой окружения до тестов | `pip install`, postgres или `migrate` упали, шаг тестов не выполнялся | Issue создаётся так же, но причина — «до тестов дело не дошло, сломано окружение» | N/A |
| Повторное падение | Открытый issue с меткой уже есть (независимо от причины) | Комментарий в него с причиной текущего прогона; новый issue **не** создаётся | N/A |
| Починка | Прогон зелёный, открытые issue с меткой есть | Все закрыты, в каждом комментарий об успехе | Сбой шага не валит прогон |
| Стабильно зелёный | Прогон зелёный, открытых issue нет | Ничего не происходит | N/A |
| Ручной прогон с feature-ветки | `github.ref_name != develop` | Оба шага пропущены | N/A |
| Issue закрыт человеком при живой проблеме | Прогон упал, issue есть, но закрыт | Создан новый — закрытые в поиске не участвуют | N/A |
| Отмена или таймаут прогона | Прогон отменён вручную либо по `timeout-minutes` | Ни оповещения, ни закрытия: `failure()` при отмене ложно, а намеренную отмену от таймаута не отличить | Ограничение задокументировано |

</frozen-after-approval>

## Code Map

- `.github/workflows/performance-tests.yml` — единственный изменяемый workflow; в исходном состоянии 94 строки, блока `permissions` нет, последний шаг — `pytest -m "performance or slow"`. После правки — два job-а: `performance` (тесты, `contents: read`) и `notify` (оповещение, `issues: write`, без checkout).
- `.github/workflows/setup-branch-protection.yml:19-23,41-72` — образец блока `permissions` и вызова `github-script` с `issues.create` и метками в этом репозитории.
- `.github/workflows/api-contract.yml:164-172` — образец `if: failure()` с привязкой к исходу конкретного шага.
- `backend/docs/testing-standards.md:38-48` — таблица «Где что исполняется»; строку про `performance-tests.yml` дополнить.

## Tasks & Acceptance

**Execution:**
- [x] `.github/workflows/performance-tests.yml` — задать `permissions: {}` на уровне workflow, чтобы дописанный позже job не унаследовал дефолт репозитория; права выдавать пожобово.
- [x] `.github/workflows/performance-tests.yml` — присвоить шагу pytest `id: tests`, отдать его исход через `outputs.tests_outcome`, оставить job-у `performance` только `contents: read`, добавить `concurrency` на уровне workflow.
- [x] `.github/workflows/performance-tests.yml` — завести отдельный job `notify` (`needs: performance`, `if: always() && github.ref_name == github.event.repository.default_branch`, `permissions: issues: write`, без checkout) с единственным шагом `github-script`, ветвящимся по `needs.performance.result`: `success` → закрыть все найденные issue, `failure` → комментарий в самый ранний либо создание нового, прочее → ничего.
- [x] `backend/docs/testing-standards.md` — вынести описание в подраздел «Nightly: как узнать о падении» с перечнем непокрытого (отмена, таймаут, ручной прогон с feature-ветки, угасший cron) и правилом чтения сигнала.

**Acceptance Criteria:**
- Given nightly упал две ночи подряд на `develop`, then в репозитории ровно один открытый issue с меткой `nightly-failure`: ссылка на первый прогон — в теле issue, на второй — комментарием. Второй issue не создаётся.
- Given прогон упал на `pip install` и шаг тестов не выполнялся, when отработал шаг оповещения, then issue создан и его текст называет причиной сбой окружения, а не падение тестов.
- Given открытый issue заведён по сбою окружения, when следующей ночью падают уже сами тесты, then комментарий уходит в тот же issue, а его заголовок остаётся верным для обеих причин.
- Given открыт issue с меткой, when очередной nightly зелёный, then issue закрыт, а прогон остаётся зелёным.
- Given закрытие одного issue упало, when открытых issue с меткой было несколько, then остальные всё равно закрыты, а прогон `performance` остаётся зелёным — `notify` отдельный job.
- Given `permissions: {}` задан на уровне workflow, when выполняется `actions/checkout@v4` в job `performance`, then checkout проходит по job-level `contents: read`.
- Given `NIGHTLY_LABEL` пуст, when отработал job `notify`, then шаг падает с `setFailed` и **ни один** issue не тронут.

## Spec Change Log

### Итерация 2 — 2026-08-13, bad_spec: оповещение вынесено в отдельный job

**Находка.** Шаговый `failure()` требует, чтобы шаг был достигнут. Job поднимает `postgres:15` и `redis:7` как service-контейнеры с health-check; если контейнер не встал, job падает на фазе «Initialize containers» и **не исполняется ни один шаг** — включая шаг оповещения. Самый вероятный вид «сломанного окружения» обслуживался веткой сообщения, до которой управление не доходит. Второй находкой того же прохода: `issues: write` был выдан всему job, то есть шагам `pip install` из PyPI и исполнению тестового кода — в публичном репозитории это право записи в issues для скомпрометированной транзитивной зависимости.

**Что изменено.** Оповещение вынесено в отдельный job `notify` с `needs: performance` и `if: always()`. Job-level `failure()` срабатывает и когда upstream-job умер на инициализации контейнеров. Job `performance` сохраняет только `contents: read` и отдаёт `steps.tests.outcome` через `outputs`; `notify` получает только `issues: write` и не делает checkout. Побочный выигрыш: оба сценария (падение и успех) обслуживает один шаг с ветвлением по `needs.performance.result`, поэтому дословно скопированные поиск issue, фильтр PR и сборка `runUrl`/метки времени перестают существовать в двух экземплярах.

**Какого состояния избегаем.** Оповещения, которое молчит именно в том классе отказов, ради которого на предыдущей итерации расширяли условие, — при документации, утверждающей «любое падение поднимает issue».

**KEEP — дополнительно к итерации 1:**

- `concurrency` на уровне workflow: параллельные перф-прогоны искажают тайминги друг друга и не видят issue друг друга.
- Трёхветочный диагноз причины (`failure` / `success` / пусто), а не отрицание одного значения.
- Проверка `created.data.assignees.length` — GitHub молча отбрасывает недопустимого assignee.
- `try/catch` вокруг итерации цикла закрытия, а не вокруг цикла целиком.
- `github.paginate` вместо одной страницы.
- Тестовый job не имеет права записи в issues.

### Итерация 1 — 2026-08-13, intent_gap по охвату сигнала

**Находка.** Оба состязательных ревьюера независимо назвали главным дефектом то, что условие `steps.tests.outcome == 'failure'` отсекает обрыв `pip install`, недоступность postgres и падение `migrate`: прогон красный, issue нет. Корень — внутри `<frozen-after-approval>`: строка матрицы «Обрыв до тестов → Issue не создаётся» противоречила Intent в том же блоке («красный nightly не заметит никто»).

**Что изменено (решение Alex).** Условие оповещения расширено до `failure()`; причина падения переехала из условия в текст сообщения и определяется по `steps.tests.outcome`. Заголовок issue сделан нейтральным к причине. Матрица дополнена строками «Сбой окружения до тестов» и «Отмена или таймаут прогона».

**Какого состояния избегаем.** Правки, которая сузила проблему вместо закрытия: раньше молчали все падения, после первой редакции молчали инфраструктурные — при том что документация утверждала наличие оповещения. Документация не является сигналом.

**KEEP — обязано пережить перегенерацию:**

- Дедупликация по метке с отсевом pull requests и `per_page: 100`.
- Закрытие **всех** найденных issue, а не первого.
- В шаге закрытия: `issues.update` до комментария, всё тело в `try/catch` с `core.warning` — немой `continue-on-error` недопустим.
- `assignees: [context.repo.owner]` — issue без адресата воспроизводит ту же тишину.
- Guard одним сравнением с `github.event.repository.default_branch`; ветвь `github.event_name == 'schedule'` избыточна — `repository` присутствует в payload `schedule` (проверено по документации GitHub).
- Метка — в `env.NIGHTLY_LABEL`, не хардкодом в четырёх местах.
- Полная метка времени и пометка «по расписанию / вручную» в сообщении.
- В комментариях workflow не упоминать состояние защиты веток: репозиторий публичный.
- Отмена и таймаут остаются непокрытыми осознанно — `always()` не применять.

## Design Notes

Поиск по метке, а не по заголовку: заголовок человек отредактирует, метку — вряд ли. `issues.listForRepo` возвращает и pull requests, поэтому результат фильтруется по отсутствию поля `pull_request`: `issues.update({state:'closed'})` по номеру PR закрыл бы именно PR.

**Причина падения — в тексте, не в условии.** Условие оповещения знает только «прогон упал»; что именно упало, определяется по `steps.tests.outcome` уже внутри скрипта. Так один и тот же issue обслуживает обе причины, и переход «сегодня сломалось окружение, завтра сами тесты» не плодит вторую задачу. Отсюда же нейтральный заголовок: причина живёт в теле и комментариях, где её можно уточнять, а заголовок остаётся верным всё время жизни issue.

**Проверка синтаксиса скриптов.** Тело `github-script` — строка внутри YAML, её не видит ни один линтер репозитория. После правки скрипты извлекаются из workflow и проверяются `node --check`; опечатка иначе вскрылась бы в момент, когда сигнал нужнее всего.

```yaml
- name: Оповестить о падении
  if: failure() && steps.tests.outcome == 'failure' && github.ref_name == github.event.repository.default_branch
  uses: actions/github-script@v7
  with:
    script: |
      const url = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
      const list = await github.rest.issues.listForRepo({
        ...context.repo, state: 'open', labels: 'nightly-failure', per_page: 10,
      });
      const open = list.data.find((i) => !i.pull_request);
      // далее: createComment(open.number) либо issues.create({labels: ['nightly-failure']})
```

## Verification

**Commands:**
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/performance-tests.yml'))"` — ожидается: разбор без исключения.
- `git diff --stat` — ожидается: ровно два файла; шаги установки, миграций и вызов pytest в diff не участвуют.
- `npx gitnexus detect-changes --scope all` — ожидается: ни один Python-символ не затронут.

**Manual checks:**
- Создание/закрытие issue проверяется только после мержа в `develop`: cron исполняется на ветке по умолчанию, а `workflow_dispatch` с feature-ветки отсекается guard-ом. После мержа — запустить вручную на `develop` и убедиться, что зелёный прогон issue не создаёт и не падает.
- Глазами проверить, что в теле issue нет ничего сверх имени workflow, ссылки, SHA и даты: репозиторий публичный.

## Suggested Review Order

**Замысел: почему оповещение — отдельный job**

- Точка входа: два job-а вместо шагов — здесь видно и охват, и разделение прав.
  [`performance-tests.yml:149`](../../.github/workflows/performance-tests.yml#L149)

- Тестовый job отдаёт исход шага наружу; пустое значение легитимно.
  [`performance-tests.yml:48`](../../.github/workflows/performance-tests.yml#L48)

- Права по умолчанию пусты: дописанный позже job не унаследует широкие.
  [`performance-tests.yml:25`](../../.github/workflows/performance-tests.yml#L25)

**Предохранители — самое ценное в диффе**

- Пустая метка вернула бы весь трекер, а зелёный прогон закрыл бы его.
  [`performance-tests.yml:171`](../../.github/workflows/performance-tests.yml#L171)

- Отбор по ветке внутри скрипта, а не в `if`: пропущенный job молчит бесследно.
  [`performance-tests.yml:180`](../../.github/workflows/performance-tests.yml#L180)

- Непроставленная метка ломает дедупликацию навсегда — проверяется и пишется в issue.
  [`performance-tests.yml:308`](../../.github/workflows/performance-tests.yml#L308)

**Логика ветвления**

- Один шаг на оба исхода; закрываются все issue, не первый.
  [`performance-tests.yml:215`](../../.github/workflows/performance-tests.yml#L215)

- Трёхветочный диагноз: «тесты», «шаг после них», «до тестов не дошло».
  [`performance-tests.yml:260`](../../.github/workflows/performance-tests.yml#L260)

- `state_reason` при закрытии: иначе «починилось» не отличить от «not planned».
  [`performance-tests.yml:232`](../../.github/workflows/performance-tests.yml#L232)

**Сопутствующее**

- Сериализация прогонов: параллельные искажают тайминги и плодят дубликаты issue.
  [`performance-tests.yml:19`](../../.github/workflows/performance-tests.yml#L19)

- Правило чтения сигнала и честный список непокрытого.
  [`testing-standards.md:68`](../../backend/docs/testing-standards.md#L68)

- Предупреждение против замены `always()` на `failure()` — сломает автозакрытие.
  [`testing-standards.md:54`](../../backend/docs/testing-standards.md#L54)
