---
baseline_commit: "e3e05a46" # HEAD develop на момент создания стори
review_head: "0830b703" # 2026-09-09, закрытие пятого ревью: сужение утверждений о произношении в docstring TextSeparator.tsx + deferred-work.md + sprint-status.yaml. Сдвинут с 100ce0c1 по тому же правилу, что и в прошлый раз — итерация трогает исходный файл (docstring), а не только метаданные. Следующий за ним 3074e9d5 — чисто документационный (одна лишь стори) и review_head не сдвигает
excluded_commits: ["4a2379ed"] # автогенерируемый блок GitNexus в AGENTS.md/CLAUDE.md (счётчик символов), к стори отношения не имеет — попал внутрь диапазона по времени, не по смыслу
# Канонический changeset стори. Область приёмки =
#   git log --oneline baseline_commit..review_head  МИНУС excluded_commits.
# review_head НЕ сдвигается документационными правками метаданных.
# Поле читается в версии story-файла на HEAD ветки, а не внутри самого review_head:
# завершающий документационный коммит с этой правкой по определению идёт последним.
---

# Story 41.8: Текстовый разделитель между бейджем, брендом и названием товара

Status: review

> 🔴 **GitNexus: `impact` по `ProductBadge` вернул `"risk": "CRITICAL"`** — 13 затронутых символов, 2 прямых вызывающих (`ProductCard`, `RecommendationsRow`), 9 затронутых процессов, 5 модулей (замер 2026-09-08 на индексе `e3e05a4`). Правка тривиальна по объёму, но узел общий: ошибка проявится сразу на `/home`, `/catalog`, `/search` и `/electric`. Риск сообщён владельцу при создании стори. Перед правкой перезамерить (Task 2) — если картина изменилась, перечитать координаты.
> 🔴 **`ProductCard.test.tsx` мокает `ProductBadge`** (`frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx:42-56`): мок возвращает голый `<span data-testid="badge-new">Новинка</span>` без разделителя. Проверка разделителя, дописанная в этот файл, проверит **мок, а не код** — ровно тот класс бесполезного теста, который был находкой ревью в 41.6. Тест разделителя пишется в **отдельном файле без `vi.mock('@/components/common/ProductBadge')`**.
> 🔴 **Разделитель обязан быть `position: absolute` (класс `sr-only`), а не текстовым узлом в потоке.** Контейнер описания — flex-колонка: `div.p-3.flex.flex-col` в compact (`ProductCard.tsx:283`) и `div.p-4.flex.flex-col` в grid (`:542`). Обычный `<span> </span>` там становится flex-элементом и добавляет строку высотой line-height — вёрстка поедет. `sr-only` выносит элемент из потока и гарантирует AC2 конструктивно.
> ⚠️ **Порядок склейки в list-layout другой: бренд → бейдж → название** (`ProductCard.tsx:393-405`). Разделителя «после бейджа» там недостаточно. Поэтому разделителей два: один внутри `ProductBadge` (после бейджа), второй — после абзаца бренда.
> ⚠️ **Vitest здесь `happy-dom` и `css: false`** (`frontend/vitest.config.mts:21,27`): CSS не подключается, `sr-only` в тестах ничего не скрывает. «Внешний вид не изменился» тестом **не доказывается** — только осмотром в браузере (Task 8). Тест охраняет DOM-структуру и текст, не раскладку.
> 🚫 **Стори не трогает бэкенд.** Ни моделей, ни сериализаторов, ни `docs/api/openapi.yaml`, ни `frontend/src/types/api.generated.ts`. **NFR-41-02 не задействуется**, `npm run generate:types` не запускается, миграций нет, pytest не гоняется.
> 🚫 **Склейка «название + цена» и «цена + Нет в наличии» не чинится** — она за границей FR-41-19 (см. AC6 и «Решения владельца по объёму»).

## Story

As a **потребитель карточки, читающий её программно** — сканер доступности, парсер каталога, аудиторский отчёт,
I want **получать текст бейджа, бренда и названия товара как отдельные слова при извлечении `element.textContent`**,
so that **карточка не выдавалась одним склеенным словом (`НовинкаBoyBoКапа`)**.

> **Роль переформулирована 2026-09-08 по решению владельца** (находка четвёртого ревью). Исходно стори была
> заведена от лица пользователя скринридера («слышать … как отдельные слова»). Собственные замеры стори эту
> постановку опровергли: в Chromium AX tree и в платформенном Windows UIA — том API, из которого дикторы
> строят речь, — бейдж, бренд и название были **тремя отдельными текстовыми узлами уже до правки**, а сам
> `TextSeparator` в этих деревьях не появляется вовсе (в AX tree помечен `ignored:uninteresting`, в UIA
> отсутствует). Склейка существует исключительно в `element.textContent`. Поэтому роль и outcome приведены
> к измеримому эффекту, который правка действительно даёт. Про произношение замерами установлено ровно
> следующее: набор и порядок **текстовых узлов** в обоих деревьях до и после совпадают, а `TextSeparator`
> в них не появляется. Структура контейнеров при этом не идентична — в UIA после правки добавился один
> уровень `[группа]` (фрагмент вокруг `<Badge>`). Фактическая речь живого диктора не снималась, поэтому
> вывода «произношение не ухудшилось» стори **не делает** — только перечисляет наблюдённое
> (см. Dev Agent Record).

**Закрывает:** FR-41-19. **Соблюдает:** NFR-41-01, NFR-41-03, NFR-41-06.

**Происхождение и честная ценность.** Исходное замечание сканера («смешение алфавитов», 16 случаев: `НовинкаBoyBoКапа`, `ХитBoyBoПояс`, `АкцияCosmorideШлем`) — **ложное**: визуально это три отдельных элемента, ошибки в тексте нет. Реальная ценность правки — корректное программное извлечение текста карточки: `element.textContent` перестаёт склеивать бейдж, бренд и название в одно слово. Так карточку читают парсеры и сканеры доступности, и именно этот путь замерен до и после правки. Улучшения чтения экранным диктором правка **не даёт и не заявляет**: замер AX tree и UIA показал, что бейдж, бренд и название были отдельными узлами и до неё, а разделитель в эти деревья не попадает. Наблюдённое этими замерами — совпадение набора и порядка текстовых узлов до и после и отсутствие разделителя в обоих деревьях; структура контейнеров при этом отличается на один уровень `[группа]` в UIA. Утверждения о фактической речи — ни «лучше», ни «не хуже» — стори не делает: живой диктор не запускался, замер вынесен в `deferred-work.md` отдельной задачей. Проверка «выделить и скопировать» ценность правки **не** подтверждает — браузер разделяет слова на границах блочных элементов и без разделителя (замеры 2026-09-08, см. Dev Agent Record). Побочно 16 строк исчезнут из следующего отчёта. Это единственная стори эпика, выведенная не из подтверждённого дефекта, — поэтому она и выполняется предпоследней.

## Acceptance Criteria

### AC1 (FR-41-19) — текст разделён при программном извлечении

**Given** карточка товара с бейджем (любой из трёх layout'ов `ProductCard`)
**When** её текстовое содержимое извлекается программно (`element.textContent`)
**Then** между текстом бейджа, названием бренда и названием товара присутствует хотя бы один пробельный символ
**And** это проверяется на реальном `ProductBadge`, а не на его тестовом моке
**And** проверка выполнена для всех трёх layout'ов: `grid`, `list`, `compact` — порядок элементов в `list` отличается (бренд → бейдж → название), и он тоже покрыт

### AC2 (FR-41-19) — внешний вид не изменился

**Given** та же карточка
**When** она отображается визуально
**Then** отступы, вёрстка и размеры прежние
**And** это обеспечено конструктивно: разделитель — `<span className="sr-only left-0 top-0">`, то есть `position: absolute` с координатами `0/0`, размером 1×1 и `clip: rect(0,0,0,0)` — вне потока, видимых символов не даёт и на размеры соседей не влияет
**And** формулировка «`margin` не добавляет» была бы неверна: утилита `sr-only` в Tailwind v4 задаёт `position:absolute; width:1px; height:1px; padding:0; **margin:-1px**; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border-width:0` (проверено в `node_modules/tailwindcss/dist`). Гарантию даёт не отсутствие `margin`, а то, что элемент вынесен из потока и обрезан до 1×1 — отрицательный внешний отступ абсолютно спозиционированного узла соседей не двигает
**And** осмотр выполнен в браузере на `/home`, `/catalog` и `/electric` при ширинах 375px и 1440px и зафиксирован в Dev Agent Record (`css: false` в конфиге Vitest означает, что тестом раскладка не проверяется)

### AC3 (FR-41-19) — карточка без бейджа и без бренда

**Given** карточка товара без активных маркетинговых флагов
**When** она отображается
**Then** лишний разделитель, пустой отступ или пустой узел не появляется
**And** это обеспечено конструктивно: разделитель бейджа живёт **внутри** `ProductBadge`, который при отсутствии флагов возвращает `null` целиком; разделитель бренда живёт **внутри** условия `{product.brand && (...)}`
**And** то же проверено для карточки без бренда, и для карточки без бейджа и без бренда одновременно

### AC4 (NFR-41-06) — доступность

**Given** отрисованный список карточек товаров
**When** выполняется проверка axe-core (`vitest-axe`)
**Then** число нарушений не превышает базис, снятый тем же тестом **до** правки
**And** базис записан в Debug Log числом, а не словом «зелено» — иначе «новых нарушений нет» ничем не подтверждено
**And** новых интерактивных элементов стори не вводит: разделитель — текстовый узел, фокус не принимает, в tab-порядок не попадает

### AC5 (NFR-41-01) — тесты и статический анализ

**Given** изменённый код
**When** прогоняется `npm run test`
**Then** существует тест самого разделителя (`frontend/src/components/common/__tests__/TextSeparator.test.tsx`), и он проверяет, что `textContent` компонента равен пробелу, а класс — `sr-only`
**And** существует тест склейки в карточке (`frontend/src/components/business/ProductCard/__tests__/ProductCard.text-separation.test.tsx`), рендерящий **реальный** `ProductBadge`
**And** тест склейки проверяет отсутствие подстрок вида `НовинкаNike` / `NikeTest Product` в `container.textContent`, а не только присутствие разделителя где-то на странице
**And** существующие тесты не сломаны: `ProductCard.test.tsx`, `ProductBadge.test.tsx`, `Badge.test.tsx` остаются зелёными без правок их ожиданий
**And** `npm run lint`, `npm run format:check` и `npx tsc --noEmit` проходят без ошибок

### AC6 (границы) — что стори НЕ делает

**Then** **не** меняется бэкенд, `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`; `npm run generate:types` не запускается, pytest не гоняется
**And** **не** меняется компонент `Badge` (`frontend/src/components/ui/Badge/Badge.tsx`) — ни варианты, ни классы, ни иконки
**And** **не** меняется логика `determineBadge` (`ProductBadge.tsx:33-76`): приоритеты флагов, тексты бейджей и условие `null` остаются как есть
**And** **не** чинится склейка «название + цена» (`Капа1 200 ₽`) и «цена + Нет в наличии» — тот же класс дефекта, но за границей FR-41-19; выносится в `deferred-work.md`
**And** **не** добавляются `aria-label`, `aria-describedby` или visually-hidden подписи к карточке — стори добавляет разделитель, а не переписывает семантику карточки
**And** **не** правится `RecommendationsRow` (компонент экспортируется из `common/index.ts`, но ни одной страницей не используется — правка внутри `ProductBadge` покрывает его автоматически, отдельного теста он не получает)
**And** **не** вводится видимый разделитель (`·`, `—`, `|`) — AC2 требует неизменного внешнего вида

## Tasks / Subtasks

- [x] **Task 1. Ветка и baseline** (все AC)
  - [x] `git switch develop; git pull` — стори 41.7 влита (`e3e05a46`), внешних зависимостей у 41.8 нет
  - [x] `git switch -c feature/story-41-8-text-separator-product-card` (прямые коммиты в `develop` запрещены)
  - [x] `git rev-parse --short HEAD` → сверить с `baseline_commit` фронтматтера, при расхождении обновить поле
  - [x] Зафиксировать базис тестов ДО правок: `cd frontend; npm run test` → число файлов/зелёных в Debug Log

- [x] **Task 2. Blast radius** (все AC)
  - [x] `npx gitnexus impact "Function:frontend/src/components/common/ProductBadge.tsx:ProductBadge" --direction upstream --repo "C:\Users\1\DEV\FREESPORT" --include-tests`
        Имя `ProductBadge` неоднозначно (`Function:` и `Const:` в одном файле) — короткую форму `npx gitnexus impact ProductBadge` CLI отклонит с `ambiguous`, нужен полный uid
  - [x] Ожидаемо `"risk": "CRITICAL"`, `impactedCount: 13`, прямые: `ProductCard`, `RecommendationsRow` (замер 2026-09-08). Расхождение → перечитать координаты в Dev Notes до правки
  - [x] То же для `ProductCard`: `npx gitnexus impact "Function:frontend/src/components/business/ProductCard/ProductCard.tsx:ProductCard" --direction upstream --repo "C:\Users\1\DEV\FREESPORT" --include-tests`
  - [x] Сообщить владельцу уровень риска (требование `project-context.md` §5) — CRITICAL уже сообщён при создании стори, повторить факт замера в Dev Agent Record

- [x] **Task 3. Компонент `TextSeparator`** (AC1, AC2, AC3)
  - [x] Создать `frontend/src/components/common/TextSeparator.tsx` — код и docstring в Dev Notes «Реализация»
  - [x] Экспортировать из `frontend/src/components/common/index.ts` рядом с остальными (добавлять в конец списка)
  - [x] Docstring и комментарии — на русском (NFR-41-03), с объяснением **почему** `sr-only`, а не пробел в потоке: иначе следующий разработчик «упростит» и сломает раскладку

- [x] **Task 4. Разделитель внутри `ProductBadge`** (AC1, AC3)
  - [x] `frontend/src/components/common/ProductBadge.tsx:85-89` — обернуть возврат во фрагмент, добавив `<TextSeparator />` **после** `<Badge>`
  - [x] Ветку `if (!badge) return null;` (`:81-83`) не трогать — именно она даёт AC3 бесплатно
  - [x] `determineBadge` и его приоритеты не трогать (AC6)
  - [x] Проверить, что `ProductBadge.test.tsx` остался зелёным без правок: `screen.getByText('25% скидка')` нормализует пробелы и продолжает находить бейдж

- [x] **Task 5. Разделитель после бренда в `ProductCard`** (AC1, AC3)
  - [x] compact-layout, `ProductCard.tsx:285-289` — `<TextSeparator />` внутри блока `{product.brand && (...)}`, сразу после `</p>`
  - [x] list-layout, `ProductCard.tsx:394-398` — то же внутри `{product.brand && (...)}`; здесь бренд стоит **перед** бейджем, поэтому разделитель разрывает пару «бренд + бейдж», а разделитель из Task 4 — пару «бейдж + название»
  - [x] grid-layout, `ProductCard.tsx:544-548` — то же
  - [x] Больше в файле не менять ничего: ни классы, ни `cn(...)`, ни `aria-label`, ни обработчики

- [x] **Task 6. `ElectricProductCard`** (AC1, AC3)
  - [x] `frontend/src/components/ui/ProductCard/ElectricProductCard.tsx:100-110` — `<TextSeparator />` внутри `{badge && (...)}`, после закрывающего `</div>` бейджа
  - [x] `:144-151` — `<TextSeparator />` внутри `{brand && (...)}`, после `</p>`
  - [x] Решение владельца 2026-09-08 — оставляем в объёме: `/electric` и `/electric/catalog` — живые маршруты прода (замер 2026-09-08: `GET https://optisport.ru/electric` → 200), карточка несёт тот же дефект и тот же порядок бейдж → бренд → название. Оставить её нетронутой значит закрыть FR-41-19 наполовину
  - [x] ~~Компонент не имеет своих тестов; заводить их в этой стори **не** требуется — схема правки идентична проверенной на `ProductCard`, по одной строке на стык~~ — **отменено находкой четвёртого ревью (Devin, 2026-09-08).** Обоснование защищало от ошибки в момент написания, но не от последующей регрессии: CI проверял только `ProductCard`, а изменён живой компонент маршрутов `/electric`. Заведён `frontend/src/components/ui/ProductCard/__tests__/ElectricProductCard.text-separation.test.tsx` (9 тестов, покрытие подтверждено четырьмя мутациями исходника) — см. Task 7 и Dev Agent Record

- [x] **Task 7. Тесты** (AC1, AC3, AC4, AC5)
  - [x] `frontend/src/components/common/__tests__/TextSeparator.test.tsx`: `textContent` равен `' '`, у элемента класс `sr-only`, тег — `span`
  - [x] `frontend/src/components/business/ProductCard/__tests__/ProductCard.text-separation.test.tsx` — **без** `vi.mock('@/components/common/ProductBadge')` и без мока `@/components/ui` (нужен настоящий `Badge`). `next/image` мокается глобально в `vitest.setup.ts:90-104`, отдельный мок не нужен; `next/link` в этих тестах работает без мока (см. существующий `ProductCard.test.tsx`)
  - [x] Фикстура: взять `mockProduct` из `ProductCard.test.tsx:74-105` (бренд `Nike`, название `Test Product`), включить `is_new: true` → ожидаемый бейдж `Новинка`
  - [x] Основная проверка — на **отсутствие склейки**, а не на присутствие пробела:
        ```ts
        const text = container.textContent ?? '';
        expect(text).not.toMatch(/НовинкаNike/);
        expect(text).not.toMatch(/NikeTest Product/);
        expect(text).toMatch(/Новинка\s+Nike\s+Test Product/);
        ```
        Для `list` порядок другой — `/Nike\s+Новинка\s+Test Product/`
  - [x] Повторить для трёх layout'ов: `grid`, `list`, `compact`
  - [x] `frontend/src/components/ui/ProductCard/__tests__/ElectricProductCard.text-separation.test.tsx` — **добавлен по находке четвёртого ревью**, планом стори не предусматривался (Task 6 изначально освобождал `ElectricProductCard` от собственных тестов). 9 тестов без моков компонентов: оба стыка, три варианта бейджа (`hit`, `new`, `sale`), AC3 в трёх конфигурациях с проверкой, какой именно разделитель уцелел, и отсутствие `tabindex`/`role`
  - [x] AC3: карточка без флагов → перед брендом нет пустого `span.sr-only` от бейджа; карточка без `brand` → нет разделителя бренда; карточка без обоих → в контейнере описания нет ни одного `span.sr-only`
  - [x] AC4: axe на списке из трёх карточек, `const results = await axe(container); expect(results.violations).toHaveLength(<базис>)` — образец вызова: `frontend/src/components/layout/__tests__/CookieSettingsButton.test.tsx:83-92`. **Базис снять этим же тестом до правок** и записать в Debug Log
  - [x] Прогон: `cd frontend; npm run test -- src/components/common src/components/business/ProductCard src/components/ui/ProductCard` (третий путь добавился вместе с тестом `ElectricProductCard`), затем полный `npm run test`

- [x] **Task 8. Проверка в браузере** (AC2)
  - [x] `docker compose --env-file .env -f docker/docker-compose.yml restart frontend` (зависимости и конфиг не менялись, пересборка не нужна); при 502 после рестарта — `docker compose --env-file .env -f docker/docker-compose.yml restart nginx`
  - [x] Открыть `http://localhost/home`, `http://localhost/catalog` (grid и list через переключатель вида), `http://localhost/electric` при 375px и 1440px
  - [x] Сверить с продом (`https://optisport.ru/home`, `/catalog`, `/electric`): отличий во внешнем виде быть не должно **вообще** — стори не меняет ни одного видимого пикселя
  - [x] Снять программное содержимое карточки в консоли: `document.querySelector('[role="article"]').textContent` → между текстом бейджа, брендом и названием есть пробел (`Хит BoyBo Кимоно…`, а не `ХитBoyBoКимоно…`). **Проверка копированием сюда не годится:** браузер сам вставляет `\r\n` на границах блочных элементов, поэтому `Ctrl+C` разделяет слова и на непропатченном коде — gate дал бы ложное «дефекта нет» (замер 2026-09-08 на проде, см. Dev Agent Record)
  - [x] Результат осмотра (ширины, страницы, вывод) записать в Dev Agent Record. `[x]` ставится только по факту — в 41.6 две ручные проверки были отмечены выполненными, хотя не выполнялись

- [x] **Task 9. Перед коммитом**
  - [x] `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — затронуты только ожидаемые символы
  - [x] `File List` собрать командой `git diff --name-status <baseline_commit>..HEAD`, а не по памяти (повторяющаяся находка ревью в 41.0, 41.4, 41.5, 41.6, 41.7)
  - [x] Дописать в `_bmad-output/implementation-artifacts/deferred-work.md` пункт про склейку «название + цена» и «цена + Нет в наличии» (AC6) — иначе находка потеряется
  - [x] Установить `review_head` на коммит, завершающий содержательную работу; документационные правки его не сдвигают
  - [x] Сообщения коммитов: `fix(story-41-8): ...` для правки компонентов, `test(story-41-8): ...` для тестов
  - [x] Коммит и push — только по явной просьбе владельца

- [ ] **Task 10. Выкат**
  - [ ] Мерж PR в `develop`, затем `develop` → `main`; на проде `git fetch origin main; git reset --hard origin/main` (не `git pull`)
  - [ ] `docker compose --env-file .env.prod -f docker/docker-compose.prod.yml up -d --build frontend` — полная пересборка; частичное копирование `.next/` даёт `Failed to find Server Action`
  - [ ] После рестарта frontend на проде — `docker compose restart nginx`, иначе nginx держит старый IP upstream и отдаёт 502
  - [ ] Проверка на проде: открыть `https://optisport.ru/catalog`, в консоли снять `document.querySelector('[role="article"]').textContent` → ожидается `Made In Russia Балетки для танцев белые350 ₽…` с пробелом между брендом и названием; эталон «до» с того же URL — склейка `Made In RussiaБалетки…` (замер 2026-09-08). **Копированием выделения не проверять** — оно разделяет слова и без правки, результат ложноотрицательный. Карточки рендерятся на клиенте, поэтому `curl` разметку с бейджами не покажет — проверка только в браузере
  - [ ] ISR к карточкам товаров отношения не имеет (данные грузятся клиентом), ручная ревалидация не требуется

### Review Findings (2026-09-08)

- [x] [Review][Patch] Заменить production-проверку копированием на проверку `element.textContent` с ожидаемыми пробелами [Task 8, строка 145; Task 10, строка 160] — реальный `Ctrl+C` уже разделяет слова на непропатченном проде, поэтому текущий gate не обнаружит отсутствие `TextSeparator`.
- [x] [Review][Patch] Синхронизировать описание эффекта `TextSeparator` с подтверждёнными наблюдениями [frontend/src/components/common/TextSeparator.tsx:6; Dev Agent Record; deferred-work.md] — `textContent` подтверждает программное разделение узлов, но проверка копирования дефект не воспроизводит, а фактическое произношение скринридером отдельно не измерялось.

### Review Findings (2026-09-08, повторное ревью Codex)

- [x] [Review][Patch] Реализовать и подтвердить screenreader-цель FR-41-19 — решение владельца: сохранить роль и цель Story («пользователь скринридера», «слышать ... как отдельные слова»). Текущий `TextSeparator` исправляет `element.textContent`, но не accessibility tree Chromium: whitespace-only `span.sr-only` отсутствует в AX tree, а соседние `StaticText`-узлы `Новинка`, `Nike`, `Test Product` остаются такими же, как до правки. Требуется выбрать доступную семантику без визуальной регрессии и проверить результат живым диктором до/после; одной проверки axe или AX tree недостаточно для утверждения о произношении. [frontend/src/components/common/TextSeparator.tsx:48; Story:24-40]
- [x] [Review][Patch] Зафиксировать отсутствующую браузерную проверку `list`-layout `/catalog` при 375px и 1440px: Task 8 требует отдельно `grid` и `list`, но таблица Dev Agent Record содержит только одну строку `/catalog` на ширину и шесть комбинаций считаются как 3 маршрута × 2 ширины. До этого AC2 нельзя считать полностью подтверждённым. [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:141-146]
- [x] [Review][Patch] Исправить ложное описание состояния ветки: Dev Agent Record утверждает, что работа лежит незакоммиченной, хотя реализация и исправления уже зафиксированы коммитами `39abfea5`, `c7017a7f` и `2bc44bd3`. [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:580-582]
- [x] [Review][Defer] Защитить расчёт скидки `ElectricProductCard` от `badge="sale"` без валидного `oldPrice`: текущий интерфейс разрешает `oldPrice?: number`, а реальные call sites выставляют `badge="sale"` по `product.is_sale`, но передают `oldPrice=undefined`, когда `discount_percent` отсутствует или равен 0; результат — видимый `-NaN%`. [frontend/src/components/ui/ProductCard/ElectricProductCard.tsx:101-109] — deferred, pre-existing
- [x] [Review][Defer] Разорвать оставшиеся склейки внутри `ElectricProductCard`: между разделителем после бейджа и брендом находятся текст кнопки избранного (`♡`/`♥`) и иногда `Нет в наличии`, поэтому `textContent` остаётся `♡Nike` или `Нет в наличииNike`; это не ломает заявленные стыки «бейдж/бренд/название», но остаётся дефектом того же класса для программного извлечения. [frontend/src/components/ui/ProductCard/ElectricProductCard.tsx:101-160] — deferred, pre-existing

### Review Findings (2026-09-08, третье ревью Codex)

- [x] [Review][Patch] Явно проверить отсутствие разделителя исчезнувшего условия отдельно для карточки без бейджа и карточки без бренда [frontend/src/components/business/ProductCard/__tests__/ProductCard.text-separation.test.tsx:97]
- [x] [Review][Patch] Синхронизировать канонический пример `TextSeparator` в Dev Notes с фактическим кодом и подтверждёнными замерами [\_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:215]

### Review Findings (2026-09-08, четвёртое ревью Devin)

- [x] [Review][Patch] Переопределить заявленную screenreader-цель как измеримый результат для парсеров и сканеров — решение владельца: код оставить; роль, outcome и формулировки критериев привести к фактическому эффекту `textContent`, поскольку собственные замеры показывают, что `TextSeparator` отсутствует в UIA и игнорируется Chromium AX tree, а озвучиваемые узлы до и после идентичны. [frontend/src/components/common/TextSeparator.tsx:48; Story:24-40,661-681]
- [x] [Review][Patch] Зафиксировать подготовленную post-commit синхронизацию `review_head=f985c849`: версия story-файла внутри коммита `f985c849` всё ещё указывает `2bc44bd3` и утверждает, что третья итерация не закоммичена, поэтому приёмка по состоянию репозитория пропускает три новых AC3-теста. Текущее незакоммиченное изменение story-файла уже исправляет метаданные, но должно попасть в следующий документационный коммит без сдвига `review_head`. [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:2-7,787-792]
- [x] [Review][Patch] Добавить сфокусированные тесты `ElectricProductCard` для разделителей после условных бейджа и бренда: runtime-компонент изменён на живых маршрутах `/electric`, но CI проверяет только другой DOM-компонент `ProductCard`, поэтому исчезновение одного из двух разделителей или вынос его из условия останется незамеченным. [frontend/src/components/ui/ProductCard/ElectricProductCard.tsx:101-160]
- [x] [Review][Patch] Обновить отложенную инструкцию: описание реализации `TextSeparator` всё ещё показывает устаревший `span.sr-only` без обязательных `left-0 top-0`, следование которому возвращает уже найденное горизонтальное переполнение `/electric`. [_bmad-output/implementation-artifacts/deferred-work.md:1029]
- [x] [Review][Patch] Исправить фактически неверное обоснование AC2: стандартный Tailwind-класс `sr-only` задаёт `margin: -1px`, поэтому утверждение «margin не добавляет» неверно; корректная гарантия — absolute positioning, clipping и подтверждённое отсутствие изменения геометрии. [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:42-48]

### Review Findings (2026-09-09, пятое ревью Codex)

- [x] [Review][Patch] Сузить недоказанное утверждение о неизменности произношения: замеры Chromium AX tree и Windows UIA подтверждают неизменность текстовых узлов и их порядка и отсутствие `TextSeparator` в деревьях, но не фактическую речь живого диктора; кроме того, UIA после правки содержит дополнительный уровень `[группа]`. Формулировки должны сообщать ровно наблюдаемый результат, без вывода «произношение не ухудшилось». [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:30-41,683-703; frontend/src/components/common/TextSeparator.tsx:17-25; _bmad-output/implementation-artifacts/deferred-work.md:1033]
- [x] [Review][Patch] Синхронизировать активные Tasks и Completion Notes с финальной реализацией: Task 6 всё ещё утверждает, что у `ElectricProductCard` нет собственных тестов и они не требуются, Task 7 не перечисляет добавленный файл из 9 тестов, а итоговое «Что сделано» показывает регрессионный вариант `<span className="sr-only">` без обязательных `left-0 top-0`. [_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md:130-138,416-422]
- [x] [Review][Patch] Синхронизировать комментарий Story 41.8 в sprint tracker с текущими ролью и outcome: tracker по-прежнему говорит «ценность в доступности» и «Alex сохранил screenreader-цель», хотя Story теперь ограничивает доказанный эффект программным `element.textContent` и прямо не заявляет улучшение диктора. [_bmad-output/implementation-artifacts/sprint-status.yaml:825-832]

## Dev Notes

### Фактическое состояние (замеры 2026-09-08, коммит `e3e05a46`)

```
GET https://optisport.ru/home      -> 200   карточки рендерятся на клиенте, в HTML бейджей нет
GET https://optisport.ru/catalog   -> 200   то же
GET https://optisport.ru/electric  -> 200   живой маршрут, ElectricProductCard
```

Сканер аудита исполняет JS и потому видел склейку; `curl` её не покажет — не считать это признаком, что дефекта нет.

### Что меняется в коде

| Файл | Тип | Что делаем |
|---|---|---|
| `frontend/src/components/common/TextSeparator.tsx` | NEW | Невидимый текстовый разделитель |
| `frontend/src/components/common/index.ts` | UPDATE | Экспорт `TextSeparator` |
| `frontend/src/components/common/ProductBadge.tsx` | UPDATE | Фрагмент вокруг `<Badge>` + `<TextSeparator />` после него |
| `frontend/src/components/business/ProductCard/ProductCard.tsx` | UPDATE | `<TextSeparator />` после абзаца бренда в трёх layout'ах (`:289`, `:398`, `:548`) |
| `frontend/src/components/ui/ProductCard/ElectricProductCard.tsx` | UPDATE | `<TextSeparator />` после бейджа (`:109`) и после бренда (`:150`) |
| `frontend/src/components/common/__tests__/TextSeparator.test.tsx` | NEW | Тест самого разделителя |
| `frontend/src/components/business/ProductCard/__tests__/ProductCard.text-separation.test.tsx` | NEW | Тест склейки на реальном `ProductBadge` + axe |
| `_bmad-output/implementation-artifacts/deferred-work.md` | UPDATE | Пункт про склейку «название + цена» |

### Где именно склеивается текст

`textContent` собирает узлы в порядке DOM, игнорируя блочность и CSS. Отсюда четыре стыка:

| Компонент / layout | Порядок в DOM | Пример склейки | Координаты |
|---|---|---|---|
| `ProductCard` `grid` | бейдж (в контейнере изображения, `absolute`) → бренд `<p>` → название `<h3>` | `НовинкаBoyBoКапа` | `ProductCard.tsx:490-492`, `:544-548`, `:551-556` |
| `ProductCard` `compact` | то же | `ХитBoyBoПояс` | `:231-233`, `:285-289`, `:292-297` |
| `ProductCard` `list` | бренд `<p>` → бейдж `<span>` → название `<h3>` | `BoyBoАкцияПояс` | `:394-399`, `:403-405` |
| `ElectricProductCard` | бейдж → бренд `<p>` → название `<h3>` | `ХитBoyBoКапа` | `ElectricProductCard.tsx:100-110`, `:144-151`, `:153-158` |
| `RecommendationsRow` | бейдж → название `<h3>` (бренда нет) | `НовинкаКапа` | `RecommendationsRow.tsx:92-94`, `:133-141` |

**Почему разделителей два, а не один.** В `list` бренд стоит перед бейджем, в остальных — после. Один разделитель внутри `ProductBadge` закрывает стык «бейдж → следующий элемент» везде; второй, после абзаца бренда, закрывает стык «бренд → следующий элемент». Вместе они покрывают оба порядка без ветвления по layout'у.

### Реализация

> **Раздел синхронизирован с фактическим кодом 2026-09-08** (находка третьего ревью). Первая редакция
> была планом до реализации и разошлась с результатом в двух местах: (1) в классе не было координат
> `left-0 top-0`, добавленных после найденной регрессии на `/electric`; (2) эффект правки описывался
> как «ломает чтение скринридером и копирование текста со страницы» — оба утверждения опровергнуты
> замерами (см. Dev Agent Record). Ниже — то, что действительно в коде.

`frontend/src/components/common/TextSeparator.tsx` — исполняемая часть, дословно:

```tsx
import React from 'react';

export const TextSeparator: React.FC = () => <span className="sr-only left-0 top-0"> </span>;

TextSeparator.displayName = 'TextSeparator';
```

Docstring компонента в файле длиннее и здесь не дублируется — **источник истины именно файл**, копия
в стори неизбежно разойдётся с ним снова. Он объясняет четыре вещи, и все четыре опираются на замеры:

1. **Что подтверждено замером.** Дефект воспроизводится только при программном извлечении текста
   (`element.textContent`) — так текст читают парсеры и сканеры доступности, этот путь замерен до и после.
2. **Что проверять бесполезно.** Ручное копирование выделения дефект не воспроизводит: браузер сам
   вставляет перевод строки на границах блочных элементов, `Ctrl+C` разделяет слова и без разделителя.
3. **Что осталось неизмеренным.** Фактическое произношение экранным диктором. Замер AX tree и
   платформенного UIA показал: бейдж, бренд и название были отдельными текстовыми узлами уже **до**
   правки, а сам разделитель в этих деревьях не появляется вовсе. Правка не ухудшает произношение,
   но и не улучшает его доказуемо — не ссылаться на это как на результат.
4. **Почему `sr-only left-0 top-0`, а не пробел в потоке и не голый `sr-only`.** Контейнеры описания
   карточки — flex-колонки (`p-3 flex flex-col` в compact, `p-4 flex flex-col` в grid), обычный
   `<span> </span>` стал бы flex-элементом и добавил строку высотой line-height. `sr-only` даёт
   `position: absolute`, но **не задаёт координат**: элемент встаёт в статическую позицию, и в
   горизонтальной ленте `/electric` разделитель последней карточки уезжал на x≈1532 при окне 1440,
   давая горизонтальную полосу прокрутки (`document.body.scrollWidth` 1533). `left-0 top-0` прижимают
   его к углу позиционированного предка. Ни координаты, ни `sr-only` не «упрощать» — обе части
   закрыты тестами `TextSeparator.test.tsx`.

`ProductBadge.tsx`, возврат (`:86-94`) — стало:

```tsx
  return (
    <>
      <Badge variant={badge.variant} className={className}>
        {badge.label}
      </Badge>
      {/* Разделяет текст бейджа и следующий за ним бренд/название (Story 41.8, FR-41-19) */}
      <TextSeparator />
    </>
  );
```

`ProductCard.tsx`, каждый из трёх блоков бренда (compact `:286-294`, list `:399-407`, grid `:553-561`):

```tsx
    {product.brand && (
      <>
        <p className="...">{product.brand.name}</p>
        {/* Разделяет бренд и соседний узел при извлечении текста (Story 41.8, FR-41-19) */}
        <TextSeparator />
      </>
    )}
```

Форма записи пробела в JSX (`{' '}` против литерального пробела) значения не имеет — Prettier нормализует
её сам; фактическое содержимое и классы охраняет `TextSeparator.test.tsx`, а не форма записи в этом примере.

### Что нельзя сломать

- `ProductBadge` возвращает `null` при отсутствии флагов (`:81-83`) — это единственный механизм, дающий AC3 для бейджа. Не заменять на `<></>`, не выносить `TextSeparator` наружу компонента.
- `determineBadge` (`:33-76`) задаёт приоритет sale → promo → new → hit → premium и тексты бейджей; их проверяют `ProductBadge.test.tsx` и блок `Badge Logic` в `ProductCard.test.tsx:296-325`.
- `Badge` — `<span>` с `inline-flex ... max-w-[200px] truncate` (`Badge/Badge.tsx:63-84`) и иконкой для вариантов `delivered/transit/cancelled/premium`. Иконки помечены `aria-hidden`, текста не дают. Компонент не трогаем.
- `ProductCard` — `forwardRef<HTMLDivElement>` (`:148`), три layout'а с ранними `return` (`:215`, `:343`, `:474`). Разделитель добавляется в каждый — пропустить один легко, поэтому тест обходит все три.
- Карточка целиком обёрнута в `Link` и несёт `role="article"` + `aria-label` вида `Товар: {name}` (`:225-226`, `:355-356`, `:484-485`). Эти атрибуты не трогаем: их проверяет блок `Accessibility` в `ProductCard.test.tsx:409-453`.
- `RecommendationsRow` экспортируется из `common/index.ts:9`, но ни одной страницей не используется — правку получает автоматически через `ProductBadge`, отдельных изменений не требует.

### Тесты: что и чем гоняем

- Только Vitest, только фронт. Окружение — **happy-dom**, CSS отключён (`vitest.config.mts:21,27`).
- `next/image` замокан глобально (`vitest.setup.ts:90-104`); `vitest-axe/extend-expect` подключён там же (`:20`), отдельный импорт матчеров не нужен, но сам `axe` импортируется в файле теста: `import { axe } from 'vitest-axe'`.
- Существующий `ProductCard.test.tsx` мокает `ProductBadge` (`:42-56`), `@/components/ui` (`:59-65`), `lucide-react` (`:36-40`) и `cn` (`:68-70`). **Эти моки в новый файл не переносить** — нужен настоящий рендер `ProductBadge` → `Badge`. Мок `lucide-react` при этом можно опустить: `Badge` тянет `CheckCircle2/Truck/X/Sparkles`, но для фикстуры с `is_new: true` иконка не используется. Мокать иконки понадобится, только если добавлять кейс `is_premium`.
- Порог покрытия фронта — 65% по всем метрикам (`vitest.config.mts:44-49`), `index.{ts,tsx}` из покрытия исключены. Новый компонент состоит из одной строки JSX и покрывается собственным тестом.
- Бэкенд не менялся → pytest и Docker-тесты **не** запускаются; порог 73 (`main.yml`, `--cov=apps --cov=freesport`) этой стори не касается.
- E2E (Playwright) не задействуется: видимого поведения стори не меняет.

### Уроки предыдущих стори эпика (41.0, 41.4, 41.5, 41.6, 41.7)

Находки ревью, повторявшиеся из стори в стори:

- **Тест, проверяющий мок, не охраняет ничего.** В 41.6 «страж размеров логотипа» сравнивал литералы между собой и оставался зелёным при неверной разметке. Здесь прямой аналог — дописать проверку разделителя в `ProductCard.test.tsx`, где `ProductBadge` замокан. Именно поэтому тест выносится в отдельный файл.
- **`File List` собирается командой, а не по памяти.** Расхождение перечня с `git diff --name-status` было находкой в 41.0, 41.4, 41.5, 41.6 и 41.7. Побочные правки (автогенерируемый счётчик GitNexus в `AGENTS.md`/`CLAUDE.md`) вносить отдельным разделом, а не выкидывать.
- **`[x]` ставится только по факту.** В 41.6 две ручные проверки были отмечены выполненными, хотя не выполнялись. Здесь тестом не закрывается ровно один пункт — осмотр в браузере (Task 8), и он же единственный, кто подтверждает AC2.
- **`review_head` устанавливается один раз** по завершении содержательной работы и не сдвигается документационными правками. Рассогласование поля с фактическими коммитами было находкой в 41.6 и 41.7.
- **Формулировка «ничего не сломалось» требует числа.** В 41.7 базис тестов снимался до правок и записывался числом; здесь то же требуется для axe-нарушений (AC4).

### Project Structure Notes

- `TextSeparator` кладётся в `frontend/src/components/common/` — тот же уровень, что `ProductBadge`: маленький переиспользуемый компонент, не UI-примитив дизайн-системы. `frontend/src/components/ui/` организован папка-на-компонент (`Badge/Badge.tsx` + `Badge/__tests__/`), `common/` — плоскими файлами с общим `common/__tests__/`. Следуем `common/`.
- Тест склейки кладётся в существующий `frontend/src/components/business/ProductCard/__tests__/` рядом с `ProductCard.test.tsx`, отдельным файлом — принятая в проекте схема.
- `sr-only` — уже используемая в проекте tailwind-утилита (17 файлов, напр. `SearchResults.tsx:56`, `checkout/ContactSection.tsx:52`); собственного класса или CSS-модуля заводить не нужно.
- Правки `frontend/src/` применяются рестартом контейнера, пересборка не нужна: зависимости и конфиг не менялись.
- `TextSeparator` не содержит состояния и обработчиков — директива `'use client'` ему не нужна; он наследует контекст файла, который его импортирует (`ProductCard` и `ElectricProductCard` уже клиентские).

### References

- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.8`] — текст стори, AC, контекст, порядок выполнения
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md:132`] — FR-41-19 и разбор ложного срабатывания «смешение алфавитов»
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md:151,155`] — NFR-41-01 (тесты), NFR-41-06 (доступность, axe-core)
- [Source: `_bmad-output/planning-artifacts/epic-41-site-audit.md:243`] — «41.8 последней: единственная стори, выведенная не из подтверждённого дефекта»
- [Source: `frontend/src/components/common/ProductBadge.tsx:33-92`] — `determineBadge`, возврат `null`, точка вставки разделителя
- [Source: `frontend/src/components/business/ProductCard/ProductCard.tsx:231-233,283-297,393-405,490-492,542-556`] — три layout'а, стыки бейдж/бренд/название
- [Source: `frontend/src/components/ui/ProductCard/ElectricProductCard.tsx:99-110,143-158`] — вторая карточка с тем же дефектом
- [Source: `frontend/src/components/common/RecommendationsRow.tsx:92-94,133-141`] — бейдж и название без бренда
- [Source: `frontend/src/components/ui/Badge/Badge.tsx:58-89`] — `Badge` как `<span>`, что и делает склейку возможной
- [Source: `frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx:42-70,74-105,296-325,409-453`] — моки (в т.ч. `ProductBadge`), фикстура, блоки Badge Logic и Accessibility
- [Source: `frontend/src/components/layout/__tests__/CookieSettingsButton.test.tsx:83-92`] — образец вызова axe
- [Source: `frontend/vitest.config.mts:21,27,44-49`] — happy-dom, `css: false`, пороги покрытия
- [Source: `frontend/vitest.setup.ts:20,90-104`] — `vitest-axe/extend-expect`, глобальный мок `next/image`
- [Source: `project-context.md` §1, §5, §6, §7] — Docker-команды, GitNexus-дисциплина, язык комментариев, правила фронта
- [Source: `_bmad-output/implementation-artifacts/Story/41-7-pdn-registry-numbers-and-login-form-justification.md`] — уроки предыдущей стори, формат плана выката

### Решения владельца по объёму (Alex, 2026-09-08)

Оба вопроса закрыты до старта разработки. Переоткрывать их в ходе реализации не нужно.

1. **`ElectricProductCard` остаётся в объёме (Task 6).** Текст эпика называет только «карточку товара» и координаты `ProductBadge.tsx`, но карточка электрической темы — второй экземпляр того же дефекта на живом маршруте `/electric`. Оставить её нетронутой значило бы закрыть FR-41-19 наполовину. Task 6 обязателен к выполнению.
2. **Склейка «название + цена» (`Капа1 200 ₽`) и «цена + Нет в наличии» не трогается.** Тот же класс дефекта, но за границей FR-41-19: двумя строками не лечится, нужен разделитель ещё на двух стыках в каждом layout'е. Объём стори не расширяется; находка фиксируется записью в `deferred-work.md` (Task 9) и остаётся в AC6 как явная граница.

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), workflow `bmad-dev-story`, 2026-09-08.

### Debug Log References

**Базис тестов ДО правок** (`cd frontend; npm run test`, ветка на `e3e05a46`):
`163 файла, 2765 passed | 16 skipped (2781)`

**Базис axe ДО правок (AC4) — 0 нарушений.** Снят тем же тестом, который потом охраняет метрику: файл
`ProductCard.text-separation.test.tsx` написан и прогнан **до** правок компонентов. В том прогоне 9 тестов
упали на склейке (дефект воспроизведён на реальном коде), а тест
`доступность (AC4) > список из трёх карточек ... axe` **прошёл** с `expect(results.violations).toHaveLength(0)`.
То есть базис = **0**, и он же остался порогом после правки. «Новых нарушений нет» подтверждено числом,
а не словом.

**RED-фаза, вывод до правок** (фрагмент):

```
AssertionError: expected 'НовинкаNikeTest ProductTest description1 200 ₽' to match /Новинка\s+Nike\s+Test Product/
Test Files  1 failed (1)
     Tests  9 failed | 6 passed (15)
```

**Базис тестов ПОСЛЕ правок:** `165 файлов, 2784 passed | 16 skipped (2800)`.
Дельта: +2 файла, +19 тестов (4 `TextSeparator` + 15 склейки). Регрессий 0.

**Статический анализ:** `npx tsc --noEmit` — exit 0; `npm run lint` (`eslint . --max-warnings=0`) — без вывода;
`npm run format:check` — `All matched files use Prettier code style!`.

**GitNexus impact (Task 2), замер 2026-09-08, индекс `e3e05a4` (`status: up-to-date`):**

| Символ | risk | impactedCount | direct | processes | modules |
|---|---|---|---|---|---|
| `Function:...common/ProductBadge.tsx:ProductBadge` | **CRITICAL** | 13 | 2 (`ProductCard`, `RecommendationsRow`) | 9 | 5 |
| `Function:...business/ProductCard/ProductCard.tsx:ProductCard` | **CRITICAL** | 14 | 7 | 8 | 4 |

Картина совпала с зафиксированной при создании стори — перечитывать координаты Dev Notes не потребовалось.
Уровень CRITICAL сообщён владельцу повторно, по факту замера (первично — при создании стори).

**GitNexus detect-changes (Task 9), `--scope all`:** `7 files, 8 symbols, 21 processes, risk: critical`.
Изменённые символы — ровно ожидаемые: `ProductCard` (×2 + `cardContent`), `ProductBadge` (×2),
`ElectricProductCard`. Плюс `AGENTS.md` / `CLAUDE.md` — автогенерируемый блок GitNexus, изменённый
до старта стори (присутствовал в `git status` на момент Task 1), к правке отношения не имеет.
Новые файлы (`TextSeparator.tsx` и два теста) в списке символов отсутствуют — созданы после индексации.

### Completion Notes List

**Что сделано.** Введён компонент `TextSeparator` — `<span className="sr-only left-0 top-0"> </span>`.
Координаты `left-0 top-0` — часть финальной реализации, а не украшение: без них разделитель встаёт
в статическую позицию и в горизонтальной ленте `/electric` выносит ширину документа за край окна
(регрессия найдена и устранена внутри стори, коммит `c7017a7f`; охраняется 5-м тестом
`TextSeparator.test.tsx`). Вставлен по одному на каждый стык: внутри `ProductBadge` (после `<Badge>` —
покрывает стык «бейдж → следующий узел» сразу во всех потребителях, включая `RecommendationsRow`)
и внутри условия `{brand && (...)}` — в трёх layout'ах `ProductCard` и в `ElectricProductCard`.
Разделителей два, а не один, потому что в list-layout порядок обратный: бренд → бейдж → название.

**AC1 — закрыт.** Тест `ProductCard.text-separation.test.tsx` рендерит настоящую цепочку
`ProductCard → ProductBadge → Badge` (моков компонентов нет), проверяет отсутствие склеек
`/НовинкаNike/`, `/NikeTest Product/` и присутствие `/Новинка\s+Nike\s+Test Product/` для `grid` и `compact`,
`/Nike\s+Новинка\s+Test Product/` — для `list`. Отдельный тест подтверждает, что рендерится реальный `Badge`
(по классу `inline-flex`), а не мок — страховка от бесполезного теста, бывшего находкой ревью 41.6.

**AC2 — закрыт измерением, а не осмотром на глаз.** Браузерные MCP-инструменты в сессии оказались недоступны,
поэтому осмотр выполнен через Playwright (`@playwright/test@1.57.0`, chromium, headless) — и получился строже
ручного: снята геометрия карточек на проде (`https://optisport.ru` — **старый код**) и локально
(`http://localhost` — **новый код**) на тех же страницах и ширинах. Совпадение попиксельное:

| Страница | Ширина | prod, до (`WxH` / `brandTop` / `h3top`) | local, после (`WxH` / `brandTop` / `h3top`) |
|---|---|---|---|
| `/home` | 375 | 180x296 / 192 / 212 | 180x296 / — / 212 |
| `/home` | 1440 | 180x296 / 192 / 212 | 180x296 / — / 212 |
| `/catalog` | 375 | 343x539 / 359 / 383 | 343x539 / 359 / 383 |
| `/catalog` | 1440 | 285x481 / 301 / 325 | 285x481 / 301 / 325 |
| `/electric` | 375 | 220x402 / — / 231 | 220x402 / — / 231 |
| `/electric` | 1440 | 220x396 / — / 235 | 220x396 / — / 235 |

Горизонтальное переполнение (`document.body.scrollWidth > clientWidth`) совпало с прод-поведением на обеих
ширинах. Computed style разделителя на живой странице: `{position: "absolute", w: 1, h: 1, text: " "}` —
элемент вне потока, ровно как требует AC2. Скриншоты всех шести комбинаций сняты в рабочий каталог сессии.

Текст тех же карточек (`textContent`), до → после:

- `/home`: `ХитRuscoSportНабор бокс. начинающих…` → `Хит BoyBo Кимоно для дзюдо…`
- `/catalog`: `Made In RussiaБалетки для танцев белые350 ₽` → `Made In Russia Балетки для танцев белые350 ₽`
- `/electric`: `Хит♡RuscoSportНабор бокс…` → `Хит ♡BoyBo Кимоно для дзюдо…`

**Побочная находка при проверке AC2: локальная БД не содержала товаров с маркетинговыми флагами.**
Секции `/home` и `/electric` фильтруют по флагу **и** по наличию
(`GET /api/v1/products/?is_hit=true&ordering=-created_at&page_size=8&in_stock=true` → `count: 0`),
поэтому карточек с бейджами локально не рендерилось вовсе и проверять было нечего. На время осмотра пяти
товарам с брендом и остатком (`variants__stock_quantity__gt=0`) проставлен `is_hit`, ещё пяти — `is_new`;
после снятия замеров **флаги сняты обратно** (`is_hit=5, is_new=5` → `False`), локальная БД возвращена в
исходное состояние. Прод не затрагивался.

**AC3 — закрыт конструктивно и тестом.** Разделитель бейджа живёт внутри `ProductBadge`, ветка
`if (!badge) return null` (`ProductBadge.tsx:81-83`) не тронута — при отсутствии флагов возвращается `null`
целиком, вместе с разделителем. Разделитель бренда — внутри `{brand && (...)}`. Тесты проходят все три
layout'а в трёх конфигурациях: без бейджа, без бренда, без обоих (`span.sr-only` → 0 элементов).

**AC4 — закрыт.** Базис axe = 0 (см. Debug Log); после правки — по-прежнему 0 на списке из трёх карточек.
Отдельный тест подтверждает, что разделитель не получает ни `tabindex`, ни `role`, то есть в tab-порядок
не попадает.

**AC5 — закрыт.** 165/165 файлов, 2784 теста зелёные. `ProductCard.test.tsx` (40 тестов),
`ProductBadge.test.tsx` (12) и `Badge.test.tsx` (30) остались зелёными **без единой правки их ожиданий** —
`screen.getByText` нормализует пробелы и продолжает находить бейджи. `tsc`, `lint`, `format:check` чисты.

**AC6 — соблюдён.** Бэкенд, `openapi.yaml`, `api.generated.ts`, `Badge.tsx`, `determineBadge` и
`RecommendationsRow` не тронуты; `generate:types` и pytest не запускались; видимых разделителей не введено.
Склейка «название + цена» вынесена в `deferred-work.md`.

**Расхождение с планом стори, которое стоит знать ревьюеру.** Пункт Task 8 «выделить мышью и скопировать →
слова разделены; это и есть исходный дефект, воспроизводимый вручную» — **неверен**. Проверено на проде
(старый код) и локально (новый): `window.getSelection().toString()` разделяет слова **в обоих случаях**,
потому что браузер вставляет перевод строки на границах блочных элементов. Ручная проверка копированием дала
бы ложное «дефекта нет». Дефект наблюдаем только через `element.textContent` — так текст читают парсеры
и сканеры доступности, — и именно этот путь замерен до/после. Произношение живым экранным диктором
в стори не измерялось (см. пункт 2 ревью ниже). Наблюдение записано в `deferred-work.md`, чтобы не тратить на него время
в будущих стори этого класса.

**Дополнительные проверки по запросу владельца (2026-09-08, после реализации).**

*1. «Выдели и скопируй» на проде — перепроверено настоящим буфером обмена.* Прошлый вывод строился на
`getSelection().toString()`; теперь замер сделан строже — Playwright с разрешениями `clipboard-read`/
`clipboard-write`, реальное нажатие `Control+C` и чтение `navigator.clipboard.readText()`.
Прод (`https://optisport.ru`, **старый код без правки**), первая карточка `/home`:

| Способ извлечения | Результат на непропатченном проде |
|---|---|
| `element.textContent` | `ХитRuscoSportНабор бокс. начинающих…` — **склеено** |
| `getSelection().toString()` | `Хит\nRuscoSport\n\nНабор бокс…` — разделено |
| Реальный буфер после `Ctrl+C` | `Хит\r\nRuscoSport\r\n\r\nНабор бокс…` — **разделено** |

То же на `/catalog` (`Made In RussiaБалетки…` в `textContent` против `Made In Russia\r\nБалетки…` в буфере)
и на `/electric`. Вывод подтверждён окончательно: **ручное копирование дефект не воспроизводит даже на
непропатченном проде** — браузер сам вставляет `\r\n` на границах блочных элементов. Пункт проверки
«выделить и скопировать» в Task 8 и Task 10 даёт ложноотрицательный результат и заменён на снятие
`textContent`. Побочно замечено: в буфер первым попадает `alt` изображения (название товара) — к стори
отношения не имеет.

*2. Причина отсутствия товаров с флагами в локальной БД — не код и не миграции.* Проверено: локально
применены все 159 миграций, `python manage.py makemigrations --check --dry-run` → `No changes detected`,
обновление бэкенда не требовалось. Маркетинговые флаги `is_hit/is_new/is_sale/is_promo/is_premium` —
**контентные данные, заполняемые только вручную через Django-админку** (`ProductAdmin`: `list_editable`,
отдельный fieldset и массовые действия «Отметить как хит» и т.п., `backend/apps/products/admin.py:384-533`).
Импорт из 1С их не трогает вовсе: `grep` по `backend/apps/integrations/` не даёт ни одного вхождения —
CommerceML этих признаков не несёт. Отсюда расхождение сред:

| Среда | Товаров | is_hit | is_new | is_sale | is_promo | is_premium |
|---|---|---|---|---|---|---|
| Прод (`products`) | 9871 | 7 | 8 | 10 | 9 | 0 |
| Локальная | 9236 | 0 | 0 | 0 | 0 | 0 |

Локальная БД наполнена импортом 1С, поэтому все флаги остались в `default=False`, и секции
«Хиты/Новинки/Акции/Распродажи» на `/home` и `/electric` рендерились пустыми (фильтр запроса —
флаг **и** `in_stock=true`). Это не дефект: чтобы локально видеть карточки с бейджами, флаги нужно
проставить руками — через админку либо разовым `update` в shell.

*3. Найдена и устранена собственная регрессия вёрстки на `/electric` — AC2 нарушался.* Обнаружена при
контрольном замере после зеркалирования флагов: на `/electric` при ширине 1440 появилась горизонтальная
полоса прокрутки (`document.body.scrollWidth` = **1533** при `clientWidth` = 1440). Проверка причастности
сделана прямым экспериментом — удалением разделителей из живого DOM: без них ширина возвращалась к 1440,
то есть переполнение давали именно они. Ранний замер этого не показал, потому что в локальной БД тогда было
вдвое меньше карточек и последняя не доезжала до края.

**Причина.** Утилита `sr-only` задаёт `position: absolute`, но **не задаёт координат**, поэтому элемент
встаёт в свою «статическую» позицию — там, где он оказался бы в потоке. В горизонтально прокручиваемой
ленте товаров на `/electric` карточки уезжают вправо за край окна, и разделители последней карточки
оказывались на `x ≈ 1532` (замер: два элемента, родители `DIV.relative.aspect-square` и блок бренда),
вынося за собой ширину документа. На `/home` и `/catalog` — сетки, а не лента, поэтому там эффекта не было.
Исходная реализация из Dev Notes (`<span className="sr-only">`) этот случай не покрывала.

**Исправление.** К классу добавлены координаты: `className="sr-only left-0 top-0"`. Они прижимают элемент
к углу ближайшего позиционированного предка, и вклад в ширину документа исчезает; `sr-only` (1×1 px,
`overflow: hidden`, `clip`) сохраняется, доступность не меняется. Причина и запрет на «упрощение» описаны
в docstring компонента, а координаты закрыты отдельным регрессионным тестом в `TextSeparator.test.tsx`
(5-й тест) — иначе следующая правка снимет их как лишние.

**Контрольный замер после исправления** (localhost, разделители удаляются из DOM и ширина сравнивается):

| Страница | Ширина окна | С разделителями | Без разделителей | Вывод |
|---|---|---|---|---|
| `/electric` | 1440 | 1440 | 1440 | совпадает |
| `/home` | 1440 | 1440 | 1440 | совпадает |
| `/catalog` | 1440 | 1440 | 1440 | совпадает |
| `/electric` | 375 | 390 | 390 | совпадает |
| `/home` | 375 | 377 | 377 | совпадает |
| `/catalog` | 375 | 377 | 377 | совпадает |

Переполнение на 375 px (390 и 377 против 375) существует и на проде **до** правки (`overflowX = true`
в замере прод-эталона) и от разделителей не зависит — к этой стори отношения не имеет.

Тесты после исправления: `165 файлов, 2785 passed | 16 skipped (2801)` (+1 к прошлому прогону — новый
регрессионный тест координат); `lint`, `format:check`, `tsc` чисты.

**Пункты ревью от 2026-09-08 — оба закрыты (2 из 2).**

✅ *Resolved review finding [Patch]: заменить production-проверку копированием на проверку `element.textContent`.*
Проверка-«ложный друг» вычищена из обоих мест, где стояла gate'ом:

- **Task 8 (строка 145)** — было «выделить мышью и скопировать → в буфере слова разделены; это и есть
  исходный дефект». Стало: снятие `document.querySelector('[role="article"]').textContent` с ожиданием
  `Хит BoyBo Кимоно…` против склейки `ХитBoyBoКимоно…`, и явное предупреждение, почему копирование
  сюда не годится. Чекбокс остаётся `[x]` по факту: замеры `textContent` до/после на трёх страницах
  уже сняты и записаны выше — новая формулировка описывает то, что реально выполнялось, а старая
  описывала то, что выполнялось и ничего не доказывало.
- **Task 10 (строка 160)** — прод-gate переписан на снятие `textContent` с эталоном «до» с того же URL
  (`Made In RussiaБалетки…` → ожидается `Made In Russia Балетки…`) и запретом проверять копированием.
  Это был единственный практический риск находки: Task 10 ещё не выполнялся, и в прежней редакции
  выкат был бы принят по проверке, которая проходит даже при полностью не выехавшей правке.

✅ *Resolved review finding [Patch]: синхронизировать описание эффекта `TextSeparator` с подтверждёнными
наблюдениями.* Формулировка «ломает чтение скринридером и копирование текста со страницы» была сильнее
замеров: копирование дефект не воспроизводит вовсе, а живой экранный диктор в стори не запускался.
Приведено в соответствие в трёх названных ревью местах:

- `frontend/src/components/common/TextSeparator.tsx` — docstring: вместо утверждения про скринридер и
  копирование теперь блок «что именно подтверждено замером» с тремя пунктами: (1) дефект виден только
  через `element.textContent` — путь парсеров и сканеров доступности, он и замерен; (2) копирование
  выделения дефект не воспроизводит, проверять им бесполезно; (3) произношение экранным диктором
  **не измерялось** — это обоснованное ожидание, а не проверенный результат.
- **Dev Agent Record** (раздел «Расхождение с планом стори») — «путь скринридера и парсера» заменено на
  «так текст читают парсеры и сканеры доступности», добавлена явная оговорка про неизмеренное произношение.
- `deferred-work.md` — в пункте про склейку «название + цена» снято «скринридер читает … одним словом»
  (замера нет) → «текст извлекается … одним словом»; в пункт про ложноотрицательность копирования
  добавлен подраздел «Что при этом осталось неизмеренным»: экранные дикторы строят речь по accessibility
  tree, а не по `textContent`, и на границах блоков делают собственную паузу — поэтому «скринридер теперь
  читает правильно» нельзя предъявлять как результат стори; нужна отдельная задача с живым диктором.

**Проверки после правок ревью.** Изменения затрагивают только текст комментариев и документации —
исполняемый код не менялся ни на символ (строка JSX `<span className="sr-only left-0 top-0"> </span>`
осталась прежней), поэтому новых тестов пункты не требуют: содержимое и классы компонента уже охраняют
5 тестов `TextSeparator.test.tsx`. Регрессионный прогон: `npm run test` → **165 файлов, 2785 passed |
16 skipped (2801)** — ровно базис, зафиксированный после исправления регрессии `/electric`, дельта 0.
`npx tsc --noEmit` — exit 0; `npm run lint` — без вывода; `npm run format:check` —
`All matched files use Prettier code style!`.

**GitNexus impact перед правкой docstring (правило `project-context.md` §5).**
`npx gitnexus impact "Function:frontend/src/components/common/TextSeparator.tsx:TextSeparator" --direction upstream --include-tests`
→ **`risk: CRITICAL`**, `impactedCount: 16`, прямых вызывающих 3 (`ProductBadge`, `ProductCard`,
`ElectricProductCard`), процессов 10, модулей 6. Индекс с момента Task 2 обновился: тогда `TextSeparator`
графу ещё не был виден (создан после индексации), теперь виден и попал в граф. Уровень CRITICAL сообщён
владельцу до внесения правки; фактического риска правка не несёт — меняется только комментарий.

**Четвёртое место синхронизировано по прямому решению владельца (Alex, 2026-09-08).** В разделе `## Story`
(строка 30) стояло «Реальная ценность правки — доступность и корректное копирование текста со страницы» —
то же утверждение, что опровергнуто находкой ревью. Раздел `## Story` обычно dev-агенту править не положено
(разрешены фронтматтер `baseline_commit`, чекбоксы, Dev Agent Record, File List, Change Log и Status), и
ревью адресовало правку только трём другим местам, поэтому в первой итерации место было оставлено с явной
пометкой. Владелец распорядился внести правку — формулировка переписана: ценность заявлена как корректное
программное извлечение текста (`textContent` — путь парсеров и сканеров доступности, замерен до/после),
улучшение чтения диктором помечено как ожидание, а не результат (речь строится по accessibility tree),
проверка копированием названа не подтверждающей ценность.

**Роль в шапке стори тогда была оставлена без изменений** («As a **пользователь скринридера** … so that
карточка товара читалась») с обоснованием «это постановка цели, а не заявление о замере». Четвёртое ревью
(Devin, 2026-09-08) справедливо указало, что после замеров AX tree и UIA такая постановка вводит в
заблуждение: цель, как она была записана, правкой не достигается в принципе. По решению владельца роль и
outcome переписаны — см. пункт 1 четвёртого ревью ниже. Этот абзац оставлен как след решения, которое
позже пересмотрено.

**Не выполнено намеренно: Task 10 (выкат).** Push и мерж — только по явной просьбе владельца
(требование Task 9). Содержательная работа **закоммичена** в ветку
`feature/story-41-8-text-separator-product-card` тремя коммитами: `39abfea5` (реализация — компонент,
разделители в `ProductBadge`, трёх layout'ах `ProductCard` и `ElectricProductCard`, 19 тестов),
`c7017a7f` (исправление собственной регрессии `/electric` — координаты `left-0 top-0` + регрессионный тест)
и `2bc44bd3` (закрытие первой итерации ревью — gate проверки и формулировки по замерам).
`review_head` установлен на `2bc44bd3`. Далее в ветке лежат только документационные коммиты
(`80cdb42c`, `381a5ba3`) и коммит `4a2379ed`, исключённый из области приёмки. Не выехало на прод
ничего: `main` правки не получал.

**Пункты повторного ревью (Codex, 2026-09-08) — все три закрыты.**

✅ *Resolved review finding [Patch]: реализовать и подтвердить screenreader-цель FR-41-19.*
Решение владельца (Alex, 2026-09-08): закрыть замером accessibility tree, исполняемый код не менять.
Замер снят в два слоя, на **одном и том же товаре**, прод (`main`, старый код без разделителя) против
локального (ветка стори, разделитель есть).

*Слой 1 — accessibility tree Chromium* (`Accessibility.getFullAXTree` через CDP, `/home`, 1440px).
Прод, **до** правки:

```
article "Товар: Набор бокс. начинающих RUSCO SPORT, черно-красный"
  generic
    generic
      StaticText "Хит"
    button "Добавить в избранное"
    image "Набор бокс. начинающих RUSCO SPORT, черно-красный"
  none [ignored:uninteresting]
    paragraph
      StaticText "RuscoSport"
    heading "Набор бокс. начинающих RUSCO SPORT, черно-красный"
      StaticText "Набор бокс. начинающих RUSCO SPORT, черно-красный"
```

Локально, **после** правки — та же структура, плюс `none [ignored:uninteresting]` на месте каждого
`TextSeparator`.

*Слой 2 — платформенный UIA* (Windows UI Automation — тот самый API, из которого NVDA и Narrator строят
речь; Chrome запущен с `--force-renderer-accessibility`, дерево снято через `System.Windows.Automation`).
Товар один и тот же — «Утяжелитель неопреновый ESPADO ES2040PK, розовый»:

| Прод, **до** правки | Локально, **после** правки |
|---|---|
| `[статья] 'Товар: Утяжелитель…'` | `[статья] 'Товар: Утяжелитель…'` |
| `  [группа]` → `[группа]` → `[текстовый] 'Акция'` | `  [группа]` → `[группа]` → `[группа]` → `[текстовый] 'Акция'` |
| `  [кнопка] 'Добавить в избранное'` | `  [кнопка] 'Добавить в избранное'` |
| `  [изображение] 'Утяжелитель…'` | `  [изображение] 'Утяжелитель…'` |
| `  [группа]` → `[текстовый] 'Espado'` | `  [группа]` → `[текстовый] 'Espado'` |
| `  [заголовок]` → `[текстовый] 'Утяжелитель…'` | `  [заголовок]` → `[текстовый] 'Утяжелитель…'` |
| `  [группа]` → `[текстовый] '635'`, `[текстовый] ' ₽'` | `  [группа]` → `[текстовый] '630'`, `[текстовый] ' ₽'` |

Разница между колонками — один лишний уровень `[группа]` (фрагмент вокруг `<Badge>`) и цена (локальная БД
чуть отличается данными). Элемента для разделителя в UIA-дереве **нет вовсе**.

**Что установлено замером.**

1. Технические утверждения ревью **верны**: whitespace-only `span.sr-only` в AX tree помечен
   `ignored:uninteresting`, в платформенном UIA-дереве не появляется совсем, а соседние текстовые узлы
   после правки те же, что до неё.
2. Но посылка, что диктор произносил карточку склеенно, замером **не подтверждается**: `Акция`, `Espado`
   и название товара были **тремя отдельными текстовыми узлами в отдельных контейнерах** (`generic` /
   `paragraph` / `heading`) уже **до** правки — на обоих слоях. Склейка существует исключительно
   в `element.textContent`.
3. Отсюда: «выбрать доступную семантику» здесь нечего — она уже корректна. Добавление озвучиваемого
   разделителя (запятая в `sr-only`, `aria-label` на группе бренд+бейдж) не исправило бы дефект, потому
   что дефекта на этом слое нет; оно добавило бы диктору лишний элемент речи и сломало бы AC1 и AC5,
   требующие `textContent` разделителя ровно `' '`.
4. Про произношение замерами установлено ровно следующее: набор и порядок **текстовых узлов** в обоих
   деревьях до и после совпадают, а `TextSeparator` в них не появляется. Структура контейнеров при этом
   не идентична — в UIA после правки виден один дополнительный уровень `[группа]` (фрагмент вокруг
   `<Badge>`, см. таблицу выше). Как эта разница отражается на фактической речи, не измерялось, поэтому
   вывод «регрессии произношения нет» здесь **не делается**: перечисляется только наблюдённое.

**Что осталось неизмеренным и почему.** Фактическая речь живого диктора не снималась. На машине установлен
только Windows Narrator, чей речевой вывод не поддаётся программному захвату; NVDA отсутствует, а его
установка — новая внешняя зависимость. По решению владельца прогон живым диктором вынесен в
`deferred-work.md` отдельной задачей. В стори **не** предъявляется ни утверждение «диктор читает лучше»,
ни утверждение «произношение не ухудшилось»: оба относятся к речи, а речь не снималась. Предъявляется
только наблюдённое в деревьях — совпадение набора и порядка текстовых узлов до и после, отсутствие
`TextSeparator` в обоих деревьях и одна структурная разница (лишний уровень `[группа]` в UIA).

✅ *Resolved review finding [Patch]: зафиксировать браузерную проверку `list`-layout `/catalog`
при 375px и 1440px.* Проверка выполнена (её действительно не было — прежняя таблица содержала только
grid-режим). Маршрут `/catalog?is_hit=true` взят затем, чтобы в list-режиме гарантированно присутствовала
карточка с бейджем: именно в этом layout'е порядок обратный (бренд → бейдж → название), и оба стыка
должны быть в кадре. Вид переключён кнопкой «Список», замеры сняты после переключения:

| Метрика | prod 375 (до) | local 375 (после) | prod 1440 (до) | local 1440 (после) |
|---|---|---|---|---|
| Размер карточки | 457x156 | **457x156** | 904x156 | **904x156** |
| `brandTop` / `h3Top` | 977 / 1001 | **977 / 1001** | 398 / 422 | **398 / 422** |
| Строка «бренд + бейдж» (`div.flex.items-center.gap-2`) | 154x20 | **154x20** | 601x20 | **601x20** |
| `body.scrollWidth` / `clientWidth` | 473 / 375 | **473 / 375** | 1440 / 1440 | **1440 / 1440** |
| `span.sr-only` в карточке | 0 | 2 | 0 | 2 |

Совпадение полное по всем геометрическим метрикам, включая строку, в которую разделитель и вставляется.
`textContent` той же карточки: прод `IngameХитМяч футбольный INGAME PRO…` — склеено; локально
`Espado Хит Гантель неопреновая Espado ES1115 голубая` — разделено (товары разные, состав каталога
у сред отличается, но порядок и стыки те же). Computed style разделителя в list-режиме:
`{position: "absolute", left: "0px", top: "0px", w: 1, h: 1, text: " "}`.
Скриншоты шести комбинаций сняты в рабочий каталог сессии.

**Побочно проверено на `/catalog` без фильтра.** Там первые карточки у сред разные (локально 9236 товаров
против 9871 на проде), и ширина карточки разошлась: прод 421x156 при `scrollWidth` 437, локально 440x156
при 456 — расхождение 19px на обеих метриках. Причастность разделителей проверена прямым экспериментом:
удаление всех `span.sr-only` из живого DOM **не меняет ни ширину карточки, ни `scrollWidth`**
(440x156 / 456 до и после удаления). Расхождение даёт разница содержимого и код других стори эпика 41,
уже влитых в `develop`, но ещё не выехавших на `main`; к стори 41.8 отношения не имеет.

**Горизонтальное переполнение `/catalog` в list-режиме при 375px существует и на проде** (`scrollWidth` 473
против `clientWidth` 375) — то есть до правки; это не регрессия стори. Записано в `deferred-work.md`.

✅ *Resolved review finding [Patch]: исправить ложное описание состояния ветки.* Абзац «Не выполнено
намеренно: Task 10» переписан: содержательная работа закоммичена тремя коммитами (`39abfea5`, `c7017a7f`,
`2bc44bd3`), `review_head` стоит на `2bc44bd3`, далее в ветке только документационные коммиты и
исключённый из области приёмки `4a2379ed`. На прод не выехало ничего.

**Проверки после закрытия повторного ревью.** Исполняемый код в этой итерации не менялся ни на символ —
правки только в стори и `deferred-work.md`, поэтому `review_head` остаётся на `2bc44bd3`.
Это подтверждено независимо: `npx gitnexus detect-changes --scope all` → **`No changes detected`**
(ни одного затронутого символа; в прошлой итерации было 7 файлов / 8 символов).
Регрессионный прогон: `npm run test` → **165 файлов, 2785 passed | 16 skipped (2801)** — ровно базис,
дельта 0. `npx tsc --noEmit` — exit 0; `npm run lint` (`eslint . --max-warnings=0`) — без вывода;
`npm run format:check` — `All matched files use Prettier code style!`.
Бэкенд не затрагивался, pytest не запускался (AC6).

**Пункты третьего ревью (Codex, 2026-09-08) — оба закрыты (2 из 2).**

✅ *Resolved review finding [Patch]: явно проверить отсутствие разделителя исчезнувшего условия отдельно
для карточки без бейджа и для карточки без бренда.* Находка верна: до правки оба кейса проверялись только
по тексту (`not.toContain('Новинка')` / `not.toContain('Nike')`), а число разделителей сверялось лишь
в третьем кейсе — «без бейджа и без бренда». То есть регрессия «разделитель вынесен из условия» ловилась
частично: вынос брендового разделителя из `{brand && (...)}` оставлял кейс «без бренда» зелёным.

В `ProductCard.text-separation.test.tsx` добавлено:

- опорный кейс на все три layout'а — у полной карточки разделителей **ровно два** (бейджа и бренда),
  чтобы числа в двух проверках ниже были не магическими константами;
- «без флагов» — `span.sr-only` остаётся **ровно один**, и это именно брендовый: его
  `previousElementSibling` — тег `P` с текстом `Nike`;
- «без бренда» — остаётся **ровно один**, и это именно бейджевый: `previousElementSibling` содержит
  `Новинка`.

**Проверено мутацией, а не только зелёным прогоном** (урок 41.6: тест, который ничего не охраняет).
Две временные мутации исходников, обе откачены через `git checkout --`:

| Мутация | Что падает | Ловила ли прежняя редакция |
|---|---|---|
| Разделитель бренда вынесен из `{product.brand && (...)}` в grid | «без бренда, grid» (ожидал 1, получил 2) + «без обоих, grid» | только «без обоих» |
| `ProductBadge` при отсутствии флагов возвращает `<TextSeparator />` вместо `null` | «без флагов» во всех трёх layout'ах + «без обоих» во всех трёх (6 падений) | только «без обоих» |

После отката обеих мутаций — 18 тестов файла зелёные (было 15, +3 опорных кейса).

✅ *Resolved review finding [Patch]: синхронизировать канонический пример `TextSeparator` в Dev Notes
с фактическим кодом и подтверждёнными замерами.* Находка верна: блок «Реализация» оставался планом,
написанным до реализации, и расходился с кодом в двух местах — класс без координат `left-0 top-0`
(добавлены позже, при устранении регрессии `/electric`) и опровергнутое замерами утверждение
«ломает чтение скринридером и копирование текста со страницы». Блок переписан:

- исполняемая часть приведена **дословно** — `<span className="sr-only left-0 top-0"> </span>`;
- docstring в стори намеренно **не дублируется**: источник истины — файл, копия разошлась бы снова.
  Вместо копии — четыре пункта, что он объясняет, и все привязаны к замерам: подтверждено только
  разделение в `textContent`; копирование выделения дефект не воспроизводит; произношение диктором
  не измерялось (AX tree и UIA до/после идентичны, разделителя в них нет); координаты `left-0 top-0`
  обязательны из-за горизонтальной ленты `/electric`;
- координаты вставок обновлены по факту: `ProductBadge.tsx:86-94`, блоки бренда `ProductCard.tsx`
  compact `:286-294`, list `:399-407`, grid `:553-561`; комментарии в примерах приведены к тем,
  что стоят в коде (`Story 41.8, FR-41-19`);
- добавлена шапка-пометка, что раздел синхронизирован по находке ревью и в чём именно расходился.

**Отступление от регламента, о котором нужно знать ревьюеру.** Раздел Dev Notes dev-агенту править
обычно не положено (разрешены фронтматтер `baseline_commit`, чекбоксы, Dev Agent Record, File List,
Change Log и Status). Здесь правка выполнена потому, что сам action item ревью адресует именно это место
(`Story:215`) и иначе не закрывается вовсе; прецедент — правка раздела `## Story` по прямому решению
владельца в итерации 1.3. Ничего, кроме блока «Реализация», в Dev Notes не тронуто.

**Проверки после закрытия третьего ревью.** Продакшн-код не менялся ни на символ — правки в тесте
и в Dev Notes. Регрессионный прогон: `npm run test` → **165 файлов, 2788 passed | 16 skipped (2804)**;
дельта к прошлому базису (2785) — **+3**, ровно три новых опорных кейса, регрессий 0.
`npx tsc --noEmit` — exit 0; `npm run lint` (`eslint . --max-warnings=0`) — без вывода;
`npm run format:check` и `prettier --check` по изменённому файлу — `All matched files use Prettier code style!`.
`npx gitnexus detect-changes --scope all` → **5 файлов, 2 символа, risk: low**; оба символа — автогенерируемый
блок GitNexus в `AGENTS.md`/`CLAUDE.md`, к стори не относящийся. Символов продакшн-кода не затронуто,
что и ожидалось. Бэкенд не трогался, pytest не запускался (AC6).

**`review_head` сдвинут на `f985c849`.** В отличие от итерации 1.4 (только документация), здесь изменён
исходный файл — `ProductCard.text-separation.test.tsx`, поэтому патч обязан попасть в область приёмки.
Коммит `f985c849` («усилить AC3 проверки числа разделителей и синхронизировать Dev Notes с кодом»)
сделан владельцем (Alex) самостоятельно, одним коммитом: тест, стори, `sprint-status.yaml` и попутный
автоблок GitNexus в `AGENTS.md`/`CLAUDE.md`. На прод по-прежнему не выехало ничего — `main` правок
не получал, Task 10 не выполнялся.

**Пункты четвёртого ревью (Devin, 2026-09-08) — все пять закрыты.**

✅ *Resolved review finding [Patch]: переопределить screenreader-цель как измеримый результат для парсеров
и сканеров.* Решение владельца: код не менять, привести формулировки к тому, что действительно замерено.
Находка верна и опирается на замеры самой стори (итерация 1.4): `TextSeparator` в платформенном UIA
отсутствует, в Chromium AX tree помечен `ignored:uninteresting`, набор озвучиваемых узлов до и после
идентичен. Прежняя редакция при этом продолжала заявлять цель «слышать … как отдельные слова» — цель,
которая правкой не достигается в принципе. Синхронизировано четыре места:

- **Роль и outcome в `## Story`** — вместо «As a пользователь скринридера … so that карточка читалась»
  теперь «As a потребитель карточки, читающий её программно (сканер доступности, парсер каталога,
  аудиторский отчёт) … so that карточка не выдавалась одним склеенным словом». Под ролью — врезка,
  объясняющая, почему постановка изменена и что именно показали замеры.
- **Абзац «Происхождение и честная ценность»** — «улучшение чтения диктором — обоснованное ожидание»
  заменено на «правка улучшения не даёт и не заявляет»: замер AX tree и UIA показал, что узлы были
  раздельными и до неё.
- **Docstring `TextSeparator.tsx`** — пункт «произношение не измерялось, улучшение — обоснованное
  ожидание» заменён на результат замера: улучшения нет, разделитель в деревьях доступности не появляется.
  Исполняемая строка не тронута.
- **Абзац Dev Agent Record «Оставлено без изменений сознательно»** (итерация 1.3) — переписан: решение
  оставить роль как «постановку цели» пересмотрено, абзац оставлен как след пересмотренного решения.

> **Уточнено в итерации 1.7** (находка пятого ревью). В обоих местах эта итерация оставляла вывод
> «подтверждена неизменность произношения» / «произношение не ухудшилось». Он шире замера: деревья
> показывают состав и порядок узлов, а не речь, и структура контейнеров в UIA после правки отличается
> на один уровень `[группа]`. Формулировки сужены до наблюдённого — см. пункт 1 пятого ревью ниже.

✅ *Resolved review finding [Patch]: зафиксировать post-commit синхронизацию `review_head`.* Находка верна:
правка метаданных лежала незакоммиченной, и любой, кто брал ветку, видел `review_head: 2bc44bd3` и
утверждение, что третья итерация не закоммичена, — то есть приёмка по состоянию репозитория пропускала
три AC3-теста. Метаданные закоммичены владельцем в `100ce0c1`. Оговорка находки «без сдвига `review_head`»
писалась в расчёте на чисто документационный коммит; здесь условие другое — итерация добавляет исходные
файлы (новый тест `ElectricProductCard.text-separation.test.tsx` и docstring `TextSeparator.tsx`), поэтому
по правилу фронтматтера они обязаны попасть в область приёмки. **Решение владельца (Alex, 2026-09-08):
сдвинуть.** `review_head` = `100ce0c1`, область приёмки — `e3e05a46..100ce0c1` минус `4a2379ed`.
Остаточный лаг в одну итерацию неустраним по построению (коммит с правильным значением не может содержать
собственный хеш) и снят оговоркой в самом фронтматтере: поле читается в версии story-файла **на HEAD
ветки**, а завершающий документационный коммит по правилу `review_head` не сдвигает.

✅ *Resolved review finding [Patch]: добавить сфокусированные тесты `ElectricProductCard`.* Находка верна
и была реальной дырой: Task 6 менял живой компонент маршрутов `/electric` и `/electric/catalog`, а
обоснование «схема правки идентична проверенной на `ProductCard`, отдельных тестов не требуется» защищало
от ошибки в момент написания, но не от последующей регрессии — CI проверял только другой DOM-компонент.
Заведён `frontend/src/components/ui/ProductCard/__tests__/ElectricProductCard.text-separation.test.tsx`,
9 тестов, без моков компонентов (рендерится настоящая цепочка `ElectricProductCard` → `ElectricBadge` /
`ElectricButton`; карточка использует обычный `<img>`, глобальный мок `next/image` к ней не относится):

- AC1 — стыки «бейдж → следующий узел» и «бренд → название» не склеены (`Хит ♡`, `Nike Test Product`);
- AC1 — у полной карточки ровно два разделителя, каждый проверен по `previousElementSibling`;
- AC1 — разделитель после бейджа не привязан к варианту: `hit`, `new`, `sale` (последний с `oldPrice`);
- AC3 — без бейджа остаётся ровно один разделитель, и это брендовый; без бренда — ровно один бейджевый;
  без обоих — ноль;
- разделители не получают ни `tabindex`, ни `role`.

**Проверено мутацией, а не зелёным прогоном** (урок 41.6). Четыре мутации исходника, все откачены через
`git checkout --`:

| Мутация `ElectricProductCard.tsx` | Падает тестов из 9 |
|---|---|
| Разделитель бейджа удалён | 6 |
| Разделитель бренда удалён | 6 |
| Разделитель бренда вынесен из `{brand && ...}` | 2 |
| Разделитель бейджа вынесен из `{badge && ...}` | 2 |

Граница, за которую тест сознательно не заходит: между разделителем бейджа и брендом в DOM стоят кнопка
избранного и оверлей «Нет в наличии», поэтому `textContent` по-прежнему содержит `♡Nike`. Это отложенная
находка повторного ревью, не регрессия 41.8, — ожиданием ни в одну сторону не фиксируется.

✅ *Resolved review finding [Patch]: обновить отложенную инструкцию в `deferred-work.md`.* Находка верна:
пункт «Исправление (когда дойдут руки)» показывал `<span className="sr-only"> </span>` — редакцию **до**
устранения регрессии `/electric`, и следование ей вернуло бы горизонтальную полосу прокрутки. Класс
приведён к фактическому (`sr-only left-0 top-0`), добавлено объяснение, почему координаты обязательны и
не «упрощаются», и указание вставлять компонент как есть, не переписывая класс руками. Попутно там же
поправлен адрес тестов — теперь их два файла — и снято то же опровергнутое замерами утверждение про
ожидаемое улучшение чтения диктором.

✅ *Resolved review finding [Patch]: исправить обоснование AC2 про `margin`.* Находка верна фактически.
Проверено в `frontend/node_modules/tailwindcss/dist`: утилита `sr-only` в Tailwind v4 разворачивается в
`position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0);
white-space:nowrap; border-width:0` — отрицательный `margin` в ней есть, и формулировка AC2 «собственных
отступов, `gap`, `margin` … не добавляет» была неверна. AC2 переписан: гарантию даёт не отсутствие
`margin`, а вынос элемента из потока (`position: absolute` + `left-0 top-0`), размер 1×1 и `clip` —
отрицательный внешний отступ абсолютно спозиционированного узла соседей не двигает.

**Проверки после закрытия четвёртого ревью.** Продакшн-код не менялся ни на символ: добавлен новый тест
и переписаны комментарии/документация. Регрессионный прогон `npm run test` → **166 файлов, 2797 passed |
16 skipped (2813)**; дельта к базису прошлой итерации (165 / 2788) — **+1 файл, +9 тестов**, ровно новый
файл, регрессий 0. `npx tsc --noEmit` — exit 0; `npm run lint` (`eslint . --max-warnings=0`) — без вывода;
`npm run format:check` — `All matched files use Prettier code style!`.
`npx gitnexus detect-changes --scope all` → **`No changes detected`**: символов продакшн-кода не затронуто,
что и ожидалось. Бэкенд не трогался, pytest не запускался, `generate:types` не запускался (AC6).

**GitNexus impact перед правкой docstring (правило `project-context.md` §5).**
`npx gitnexus impact "Function:frontend/src/components/common/TextSeparator.tsx:TextSeparator"
--direction upstream --include-tests` → **`risk: CRITICAL`**, `impactedCount: 16`, прямых вызывающих 3
(`ProductBadge`, `ProductCard`, `ElectricProductCard`), процессов 10, модулей 6 — картина та же, что в
итерации 1.3. Уровень CRITICAL сообщён владельцу до внесения правки; фактического риска правка не несёт —
менялся только комментарий. Индекс на момент замера — `f985c84`, `status: up-to-date`.

**Состояние ветки.** Коммиты этой итерации сделаны владельцем (Alex): `eaeafb2e`
(`test(story-41-8)` — тест разделителей `ElectricProductCard`) и `100ce0c1` (`docs(story-41-8)` — стори,
`deferred-work.md`, docstring `TextSeparator.tsx`). `review_head` сдвинут на `100ce0c1`. Правки самой
этой записи (Dev Agent Record, File List, Change Log, чекбоксы, `review_head`, Status) уходят завершающим
документационным коммитом и `review_head` не сдвигают. Task 10 не выполнялся: на прод не выехало ничего,
`main` правок не получал.

**Пункты пятого ревью (Codex, 2026-09-09) — все три закрыты.**

✅ *Resolved review finding [Patch]: сузить недоказанное утверждение о неизменности произношения.*
Находка верна. Прошлые итерации, сняв заявление «диктор читает лучше», подставили на его место второе
утверждение того же класса — «произношение не ухудшилось» / «регрессии произношения нет». Оно тоже про
речь, а речь не снималась: замерены **деревья**, а не произнесённое. Вдобавок «набор и порядок
озвучиваемых узлов идентичны» умалчивало о единственной наблюдённой разнице — в UIA после правки
появился дополнительный уровень `[группа]` (фрагмент вокруг `<Badge>`), и он виден прямо в таблице
итерации 1.4, на которую эти формулировки ссылались.

Формулировки сужены до наблюдаемого в местах, названных находкой:

- **Врезка под ролью (`## Story`)** — вместо «что подтверждено про произношение — только его
  неизменность» теперь перечисление: набор и порядок **текстовых узлов** до и после совпадают,
  `TextSeparator` в деревьях не появляется, структура контейнеров отличается на один уровень `[группа]`
  в UIA, речь не снималась, вывода «не ухудшилось» стори не делает.
- **Абзац «Происхождение и честная ценность»** — «подтверждена только неизменность произношения»
  заменено на перечисление наблюдённого и явное «утверждения о фактической речи — ни „лучше“,
  ни „не хуже“ — стори не делает».
- **Dev Agent Record, «Что установлено замером», п. 4** — переписан: вместо «регрессии произношения
  правка не вносит» перечисляется наблюдённое, разница `[группа]` названа явно, и указано, что её
  влияние на речь не измерялось.
- **Dev Agent Record, «Что осталось неизмеренным»** — снято «предъявляется, что произношение
  не ухудшилось»; предъявляется только состояние деревьев.
- **`TextSeparator.tsx`, docstring** (пункт 3 блока «что подтверждено замером») — та же правка:
  «Подтверждено ровно одно: произношение не ухудшилось» → «Наблюдено ровно это: …», плюс запрет
  ссылаться на компонент и как на «не ухудшилось». Исполняемая строка не тронута.
- **`deferred-work.md`** — в обоих пунктах: «правка даёт корректное `textContent` и неизменное
  произношение» → «даёт корректное `textContent`, и это всё, что замерено»; «достаточно, чтобы
  утверждать „регрессии произношения нет“» → «достаточно, чтобы утверждать „набор и порядок текстовых
  узлов не изменились“», с явным упоминанием лишнего уровня `[группа]`.

Исторический блок четвёртого ревью в Dev Agent Record оставлен как след (он описывает, что делалось
тогда), но снабжён врезкой «Уточнено в итерации 1.7» — иначе запись снова расходилась бы с фактом.

✅ *Resolved review finding [Patch]: синхронизировать активные Tasks и Completion Notes с финальной
реализацией.* Находка верна во всех трёх местах — расхождение накопилось за итерации 1.5–1.6:

- **Task 6, последний подпункт** — стоял `[x]` на утверждении «компонент не имеет своих тестов;
  заводить их в этой стори **не** требуется», которое четвёртое ревью отменило, а тест по нему завело.
  Подпункт зачёркнут с пометкой «отменено находкой четвёртого ревью» и ссылкой на заведённый файл;
  сам факт исходного решения сохранён — он объясняет, почему теста не было в плане.
- **Task 7** — добавлен подпункт про `ElectricProductCard.text-separation.test.tsx` (9 тестов, без моков
  компонентов, оба стыка, три варианта бейджа, AC3 в трёх конфигурациях); в подпункте прогона к путям
  добавлен `src/components/ui/ProductCard` — прежняя команда этот файл не запускала вовсе.
- **Completion Notes, «Что сделано»** — показывал `<span className="sr-only"> </span>`, то есть редакцию
  **до** устранения регрессии `/electric`. Это тот же дефект, что четвёртое ревью нашло в `deferred-work.md`
  и Dev Notes, но третье его вхождение осталось непоправленным. Класс приведён к фактическому
  `sr-only left-0 top-0`, добавлено объяснение, почему координаты обязательны, и ссылка на коммит
  `c7017a7f` и охраняющий их 5-й тест `TextSeparator.test.tsx`.

Оставлены без правки два исторических упоминания голого `sr-only` (Dev Agent Record о причине регрессии
и о прежней редакции `deferred-work.md`) — там он и должен стоять, это описание состояния «до».

✅ *Resolved review finding [Patch]: синхронизировать комментарий Story 41.8 в sprint tracker.*
Находка верна. Шапочный комментарий говорил «ценность в доступности», а датированная запись — «Alex
сохранил screenreader-цель»; и то и другое пересмотрено четвёртым ревью, запись о котором в трекере
вообще отсутствовала (журнал обрывался на третьем ревью). Исправлено: шапочный комментарий переписан
на фактический эффект (`element.textContent`, улучшение чтения диктором не заявляется, с указанием
основания — замеры AX tree и UIA); запись от 2026-09-08 о сохранении screenreader-цели оставлена как
исторический факт с пометкой «решение пересмотрено четвёртым ревью, см. запись ниже»; добавлена
пропущенная запись о четвёртом ревью (5 finding, переопределение роли, новый тест, `review_head`
на `100ce0c1`, 166 файлов / 2797 passed). YAML перечитан парсером после правки — валиден.

**Проверки после закрытия пятого ревью.** Исполняемый код не менялся ни на символ: правки — комментарий
в `TextSeparator.tsx` и три документа. Регрессионный прогон `npm run test` → **166 файлов, 2797 passed |
16 skipped (2813)** — ровно базис прошлой итерации, дельта **0**. `npx tsc --noEmit` — exit 0;
`npm run lint` (`eslint . --max-warnings=0`) — без вывода; `npm run format:check` —
`All matched files use Prettier code style!`. `npx gitnexus detect-changes --scope all` →
**`No changes detected`**: символов продакшн-кода не затронуто, что и ожидалось. Бэкенд не трогался,
pytest и `generate:types` не запускались (AC6).

**GitNexus impact перед правкой docstring (правило `project-context.md` §5).**
`npx gitnexus impact "Function:frontend/src/components/common/TextSeparator.tsx:TextSeparator" --direction upstream --include-tests --repo "C:\Users\1\DEV\FREESPORT"`
→ **`risk: CRITICAL`**, `impactedCount: 16`, прямых вызывающих 3 (`ProductBadge`, `ProductCard`,
`ElectricProductCard`), процессов 10, модулей 6 — картина та же, что в итерациях 1.3 и 1.6.
Индекс `100ce0c`, `status: up-to-date`. Уровень CRITICAL сообщён владельцу до внесения правки;
фактического риска она не несёт — менялся только комментарий. Замечание к воспроизводимости: без
`--repo` команда теперь падает с `Multiple repositories indexed` — в индексе появился второй клон
(`C:\Users\1\DEV\FREESPORT-pr117`), поэтому параметр обязателен, как и записано в Task 2.

**Состояние ветки и `review_head`.** Правки итерации закоммичены владельцем (Alex, 2026-09-09) по
рекомендованной схеме двух коммитов:

| Коммит | Состав | Сдвигает `review_head`? |
|---|---|---|
| `0830b703` | `TextSeparator.tsx` (docstring), `deferred-work.md`, `sprint-status.yaml` | **да** — трогает исходный файл |
| `3074e9d5` | только сама стори (Tasks, Dev Agent Record, File List, Change Log, Status) | нет — чисто документационный |

`review_head` = **`0830b703`**, область приёмки — `e3e05a46..0830b703` минус `4a2379ed`. Правило
соблюдено в обе стороны: патч с исходным файлом в приёмку входит, документационный коммит поля
не двигает. Остаточный лаг в одну итерацию тот же, что и раньше, и неустраним по построению — коммит
с правильным значением не может содержать собственный хеш; снят оговоркой во фронтматтере (поле
читается в версии стори **на HEAD ветки**). Эта запись и сама правка поля уходят завершающим
документационным коммитом и `review_head` не сдвигают.

Task 10 не выполнялся: на прод не выехало ничего, `main` правок не получал.

### File List

Собрано командами `git diff --name-status e3e05a46` и `git status --short`, не по памяти.

**Новые файлы:**

| Файл | Назначение |
|---|---|
| `frontend/src/components/common/TextSeparator.tsx` | Невидимый текстовый разделитель (`span.sr-only left-0 top-0`). Пункт 2 первого ревью: docstring переписан на блок «что подтверждено замером». Четвёртое ревью: пункт про произношение приведён к результату замера — улучшения нет, разделитель в AX tree и UIA не появляется. Пятое ревью: снят и второй вывод о речи («произношение не ухудшилось») — docstring перечисляет только наблюдённое в деревьях, включая лишний уровень `[группа]` в UIA. Исполняемый код за все три итерации не менялся |
| `frontend/src/components/common/__tests__/TextSeparator.test.tsx` | Тест разделителя: содержимое, класс, тег, отсутствие фокуса, регрессия координат `left-0 top-0` (5 тестов) |
| `frontend/src/components/business/ProductCard/__tests__/ProductCard.text-separation.test.tsx` | Тест склейки на реальном `ProductBadge` + axe. Третье ревью: AC3 усилен — опорный кейс «у полной карточки ровно два разделителя» и явные проверки, что при исчезнувшем условии остаётся ровно один и именно тот (по `previousElementSibling`). Покрытие подтверждено двумя мутациями исходников, обе откачены. 18 тестов (было 15) |
| `frontend/src/components/ui/ProductCard/__tests__/ElectricProductCard.text-separation.test.tsx` | Тест разделителей второй карточки (маршруты `/electric`) — находка четвёртого ревью. Без моков компонентов; AC1 (оба стыка, три варианта бейджа) и AC3 (без бейджа / без бренда / без обоих, с проверкой, какой именно разделитель уцелел). Покрытие подтверждено четырьмя мутациями исходника, все откачены. 9 тестов. Пятое ревью: файл внесён в Task 7 и в команду прогона — прежде он не был указан ни там, ни там |

**Изменённые файлы:**

| Файл | Что изменено |
|---|---|
| `frontend/src/components/common/ProductBadge.tsx` | Импорт `TextSeparator`; возврат обёрнут во фрагмент, `<TextSeparator />` после `<Badge>` |
| `frontend/src/components/common/index.ts` | Экспорт `TextSeparator` |
| `frontend/src/components/business/ProductCard/ProductCard.tsx` | Импорт `TextSeparator`; разделитель после абзаца бренда в трёх layout'ах (compact, list, grid) |
| `frontend/src/components/ui/ProductCard/ElectricProductCard.tsx` | Импорт `TextSeparator`; разделитель после бейджа и после бренда |
| `_bmad-output/implementation-artifacts/deferred-work.md` | Два пункта: склейка «название + цена»; ложноотрицательность ручной проверки копированием. Пункт 2 ревью: снято недоказанное «скринридер читает одним словом», добавлен подраздел «Что при этом осталось неизмеренным» (произношение живым диктором). Повторное ревью: добавлены два пункта — прогон живым диктором как отдельная задача (с итогом замеров AX tree и UIA) и пре-существующее горизонтальное переполнение `/catalog` в list-режиме при 375px. Четвёртое ревью: инструкция по вставке `TextSeparator` приведена к фактическому классу `sr-only left-0 top-0` с объяснением, почему координаты обязательны; адрес тестов расширен на второй файл; снято опровергнутое замерами ожидание улучшения чтения диктором. Пятое ревью: в обоих пунктах снят вывод «неизменное произношение» / «регрессии произношения нет» — сообщается только состояние деревьев, с упоминанием лишнего уровня `[группа]` в UIA |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Статус стори: `ready-for-dev` → `in-progress` → `review` (и обратно на каждой итерации ревью). Пятое ревью: шапочный комментарий переписан под фактический эффект (`element.textContent`, улучшение чтения диктором не заявляется), запись о сохранении screenreader-цели помечена как пересмотренная, добавлена пропущенная запись о четвёртом ревью |
| `_bmad-output/implementation-artifacts/Story/41-8-text-separator-badge-brand-product-name.md` | Чекбоксы, Dev Agent Record, File List, Change Log, Status, `review_head`. Третье ревью: дополнительно синхронизирован блок Dev Notes «Реализация». Четвёртое ревью: переписаны роль и outcome в `## Story` и обоснование AC2 — оба места названы самими action item'ами (`Story:24-40`, `Story:42-48`), иначе пункты не закрываются. Пятое ревью: сужены формулировки о произношении во врезке роли, абзаце ценности и двух местах Dev Agent Record; синхронизированы Task 6, Task 7 и «Что сделано» |

**Побочные правки, к стори не относящиеся** (присутствовали в рабочем дереве до её старта, зафиксированы
в `git status` на момент Task 1; перечислены, чтобы не потерялись при коммите):

| Файл | Что это |
|---|---|
| `AGENTS.md` | Автогенерируемый блок GitNexus (счётчик символов и связей) |
| `CLAUDE.md` | То же |

## Change Log

| Дата | Версия | Описание | Автор |
|---|---|---|---|
| 2026-09-09 | 1.7 | Закрыты находки пятого ревью (Codex) — 3 из 3. (1) Сужены недоказанные утверждения о произношении: прошлые итерации, сняв «диктор читает лучше», подставили «произношение не ухудшилось» — утверждение того же класса, тоже о речи, которая не снималась. В шести местах (врезка роли, абзац ценности, два места Dev Agent Record, docstring `TextSeparator.tsx`, два пункта `deferred-work.md`) оставлено только наблюдаемое: набор и порядок текстовых узлов до и после совпадают, `TextSeparator` в деревьях не появляется, структура контейнеров отличается на один уровень `[группа]` в UIA, влияние этой разницы на речь не измерялось. (2) Синхронизированы Tasks и Completion Notes с финальной реализацией: подпункт Task 6 «тестов не требуется» зачёркнут как отменённый четвёртым ревью, в Task 7 добавлен `ElectricProductCard.text-separation.test.tsx` и путь `src/components/ui/ProductCard` в команду прогона, в «Что сделано» класс исправлен на фактический `sr-only left-0 top-0` (показывался регрессионный вариант без координат). (3) Комментарий стори в `sprint-status.yaml` приведён к текущим роли и outcome, добавлена пропущенная запись о четвёртом ревью. Исполняемый код не менялся: 166 файлов, 2797 passed | 16 skipped — дельта 0, `tsc`/`lint`/`format:check` чисты, `detect-changes --scope all` → `No changes detected`. `impact` по `TextSeparator` — CRITICAL, 16 символов, 3 прямых, сообщено владельцу до правки. `review_head` сдвинут на `0830b703` — коммит с docstring (исходный файл); следующий за ним `3074e9d5` чисто документационный и поля не двигает | Amelia (Dev Agent) |
| 2026-09-08 | 1.6 | Закрыты находки четвёртого ревью (Devin) — 5 из 5. (1) Роль и outcome стори переопределены под фактический эффект: вместо «пользователь скринридера / слышать как отдельные слова» — «потребитель карточки, читающий её программно», по решению владельца; то же утверждение синхронизировано в абзаце ценности, docstring `TextSeparator.tsx` и в устаревшем абзаце Dev Agent Record. Основание — собственные замеры итерации 1.4: узлы в AX tree и UIA идентичны до и после, разделитель в этих деревьях не появляется. (2) `review_head` сдвинут с `f985c849` на `100ce0c1` по решению владельца: итерация добавляет исходные файлы, они обязаны попасть в область приёмки; во фронтматтер добавлена оговорка, что поле читается на HEAD ветки. (3) Заведён `ElectricProductCard.text-separation.test.tsx` — 9 тестов на оба разделителя живой карточки `/electric`, без моков компонентов; покрытие подтверждено четырьмя мутациями исходника (удаление каждого разделителя и вынос каждого из своего условия), все откачены. (4) В `deferred-work.md` инструкция по вставке `TextSeparator` приведена к фактическому классу `sr-only left-0 top-0` — прежняя редакция вернула бы регрессию `/electric`. (5) Обоснование AC2 исправлено: `sr-only` в Tailwind v4 задаёт `margin: -1px` (проверено в `node_modules/tailwindcss/dist`), гарантию даёт вынос из потока, размер 1×1 и `clip`, а не отсутствие `margin`. Продакшн-код не менялся: 166 файлов, 2797 passed | 16 skipped (дельта +9 = новый файл), `tsc`/`lint`/`format:check` чисты, `detect-changes --scope all` → `No changes detected`. `impact` по `TextSeparator` — CRITICAL, 16 символов, 3 прямых, сообщено владельцу до правки | Amelia (Dev Agent) |
| 2026-09-08 | 1.5 | Закрыты находки третьего ревью (Codex) — 2 из 2. (1) AC3: в `ProductCard.text-separation.test.tsx` добавлены опорный кейс «у полной карточки ровно два разделителя» и явные проверки для карточки без бейджа и карточки без бренда — остаётся ровно один разделитель, и проверено, что именно тот (через `previousElementSibling`). Прежняя редакция ловила вынос разделителя из условия только кейсом «без обоих». Покрытие подтверждено двумя мутациями исходников (вынос брендового разделителя из `{brand && ...}`; возврат разделителя вместо `null` в `ProductBadge`) — обе откачены. (2) Блок Dev Notes «Реализация» синхронизирован с фактическим кодом: класс `sr-only left-0 top-0` дословно, опровергнутое замерами утверждение про скринридер и копирование убрано, координаты вставок обновлены, docstring намеренно не дублируется (источник истины — файл). Продакшн-код не менялся: 165 файлов, 2788 passed | 16 skipped (дельта +3 = три новых кейса), `tsc`/`lint`/`format:check` чисты, `detect-changes` — 5 файлов / 2 символа (только автоблок GitNexus), risk low. `review_head` сдвинут на `f985c849` (коммит владельца): изменён исходный файл, а не только документация | Amelia (Dev Agent) |
| 2026-09-08 | 1.4 | Закрыты находки повторного ревью (Codex) — 3 из 3. (1) Screenreader-цель FR-41-19: снят замер accessibility tree в двух слоях (Chromium AX tree через CDP + платформенный Windows UI Automation) на одном товаре, прод «до» против локального «после». Технические утверждения ревью подтвердились, но посылка о склейке в произношении — нет: бейдж, бренд и название были тремя отдельными текстовыми узлами в отдельных контейнерах уже до правки, склейка существует только в `textContent`. Решение владельца — закрыть замером, код не менять; прогон живым диктором вынесен в `deferred-work.md` (на машине только Narrator, NVDA — новая зависимость). (2) Выполнена недостающая браузерная проверка `list`-layout `/catalog` при 375px и 1440px (маршрут `?is_hit=true`, чтобы в кадре была карточка с бейджем): геометрия карточки, строки «бренд + бейдж», координат бренда и заголовка и `scrollWidth` совпали с прод-эталоном полностью. Расхождение 19px на `/catalog` без фильтра проверено экспериментом с удалением разделителей — к стори не относится. (3) Исправлено ложное утверждение о незакоммиченной работе: перечислены `39abfea5`, `c7017a7f`, `2bc44bd3`. Исполняемый код не менялся — `review_head` остаётся на `2bc44bd3` | Amelia (Dev Agent) |
| 2026-09-08 | 1.3 | Закрыты находки код-ревью — 2 из 2. (1) Проверка «выделить и скопировать» убрана из Task 8 и Task 10 и заменена на снятие `element.textContent` с эталоном «до»: прежний gate проходил и на непропатченном коде, то есть выкат мог быть принят при не выехавшей правке. (2) Формулировка эффекта `TextSeparator` приведена к замерам в трёх местах (docstring компонента, Dev Agent Record, `deferred-work.md`): подтверждено программное разделение через `textContent`, копирование дефект не воспроизводит, произношение экранным диктором не измерялось. Исполняемый код не менялся; регрессия 0 — 165 файлов, 2785 passed, `tsc`/`lint`/`format:check` чисты. `impact` по `TextSeparator` (индекс обновился, символ стал видим графу): CRITICAL, 16 символов, 3 прямых, сообщено владельцу. По решению владельца дополнительно синхронизирован раздел `## Story` (строка 30) — четвёртое место с тем же опровергнутым утверждением. Работа закоммичена как `2bc44bd3`, `review_head` сдвинут с `c7017a7f` на него: патч трогает исходный файл, а не только метаданные. Автоблок GitNexus в `AGENTS.md`/`CLAUDE.md` вынесен отдельным коммитом `4a2379ed` — к стори не относится и в область приёмки не входит. Status → review | Amelia (Dev Agent) |
| 2026-09-08 | 1.2 | Найдена и устранена собственная регрессия вёрстки: `sr-only` без координат выносил разделитель за правый край в горизонтальной ленте `/electric` (scrollWidth 1533 при окне 1440). Добавлены `left-0 top-0` + регрессионный тест. Замер после правки — ширина документа с разделителями и без совпадает на всех трёх страницах и обеих ширинах. Тесты 2785 passed | Amelia (Dev Agent) |
| 2026-09-08 | 1.1 | По запросу владельца: (1) проверка «выдели и скопируй» на проде повторена настоящим буфером обмена (`Ctrl+C` + `clipboard.readText`) — дефект копированием не воспроизводится и на старом коде, вывод подтверждён; (2) выяснена причина отсутствия флагов в локальной БД — контентные поля, заполняются только через админку, импортом 1С не приходят; миграции все применены, обновление бэкенда не требовалось. Коммит владельца `39abfea5`, `review_head` проставлен | Amelia (Dev Agent) |
| 2026-09-08 | 1.0 | Реализация стори 41.8: компонент `TextSeparator`; разделители в `ProductBadge`, трёх layout'ах `ProductCard` и `ElectricProductCard`; 19 новых тестов. AC2 подтверждён попиксельным сравнением prod/local через Playwright, базис axe = 0. Tasks 1–9 выполнены, Task 10 (выкат) — по решению владельца. Статус → review | Amelia (Dev Agent) |
