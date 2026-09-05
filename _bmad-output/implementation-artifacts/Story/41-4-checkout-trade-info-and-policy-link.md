---
baseline_commit: 87b00945
review_head: 99358186
# Канонический changeset стори. Область приёмки =
#   git log --oneline 87b00945..review_head  МИНУС excluded_commits.
# review_head устанавливается один раз по завершении содержательной работы и
# НЕ сдвигается документационными правками метаданных.
excluded_commits: []
---

# Story 41.4: Торговая информация и ссылка на политику при оплате

Status: review

> 🔴 **AC эпика про `/oferta` устарел — ссылаться нужно на `/partners#returns`.** Текст `### Story 41.4` в эпике говорит «ссылка на условия возврата (`/oferta`)», но уточнение к FR-41-15 от 2026-08-30 (прод-верификация стори 41.5) это опровергло: **в тексте оферты слов «возврат» и «обмен» нет ни одного**, там только претензионный порядок (п. 8, срок ответа 10 дней). Фактические условия возврата живут в `frontend/src/app/(blue)/partners/page.tsx:154-175`, раздел «Рекламации и возвраты». Ссылка на `/oferta` формально закрыла бы AC и **не** закрыла бы требование ЗоЗПП. Решение владельца 2026-09-05: **`/partners#returns`**, якорь заводится этой же стори.
> 🔴 **Якоря `id` на `/partners` нет ни одного** (`grep -n "id=" partners/page.tsx` пуст). Без `id="returns"` на секции `#returns` молча деградирует в переход на верх длинной страницы условий сотрудничества. Добавление якоря — часть стори, а не опция.
> 🟠 **Мёртвая ссылка «Возврат» → `/returns` в подвале чинится здесь** (решение владельца 2026-09-05, расширение объёма эпика принято осознанно). Маршрута `returns` нет ни в `frontend/src/app/`, ни среди опубликованных CMS-слагов (на проде их три: `oferta`, `privacy-policy`, `requisites`). До стори 41.0 дефект был невидим — адрес отдавал 200 с `noindex`; после 41.0 это **настоящий 404**. Адрес зафиксирован зелёным тестом `Footer.test.tsx:72` — тест правится вместе со ссылкой.
> ⚠️ **Плейсхолдеров-нарушителей три, а не два.** `example@mail.com` (`ContactSection.tsx:44`), `Формат: +7XXXXXXXXXX` (`ContactSection.tsx:65`) и то же `XXXXXXXXXX` в тексте ошибки Zod (`checkoutSchema.ts:16`) — последний виден пользователю ровно в момент ошибки, то есть чаще подсказки. Правятся все три (решение владельца 2026-09-05). Ломаются **два теста**: `ContactSection.test.tsx:122` и `CheckoutForm.test.tsx:210`.
> 🚫 **Чекбокс согласия в форме заказа НЕ добавляется.** Создание заказа защищено `IsAuthenticated` (`backend/apps/orders/views.py:37`), согласие получено при регистрации. Требование FR-41-20 ограничено **информированием** — ссылкой. Исходное требование про чекбокс снято решением Alex 2026-08-24, номер FR переиспользован.
> 🚫 **Стори не трогает бэкенд.** `openapi.yaml`, типы фронта, сериализаторы, миграции, `UserConsent` — вне объёма. NFR-41-02 не задействуется: контракт API не меняется.
> 🟢 **Blast radius LOW.** `npx gitnexus impact` (2026-09-05, коммит 87b00945): `OrderSummary` — 3 узла, risk LOW, процесс `CheckoutPage`; `ContactSection` — 3 узла, risk LOW, тот же процесс; `CartSummary` — 2 узла, risk LOW, процесс `CartPageRoute`. Ни одного HIGH/CRITICAL.

## Story

As a **покупатель**,
I want **видеть итоговую сумму, условия возврата и способ связаться с поддержкой в момент оформления заказа**,
so that **я принимал решение об оплате, располагая всей обязательной информацией**.

**Закрывает:** FR-41-15, FR-41-16, FR-41-18, FR-41-20. **Соблюдает:** NFR-41-01, NFR-41-03, NFR-41-06.

## Acceptance Criteria

### AC1 (FR-41-15) — условия возврата и поддержка рядом с оплатой

**Given** страница оформления заказа (`/checkout`) с непустой корзиной
**When** она отображается
**Then** внутри блока `data-testid="order-summary"` — того же, где кнопка «Оформить заказ», — присутствует блок `data-testid="returns-support-notice"`
**And** в нём ссылка с доступным именем `Условия возврата и рекламаций` и `href="/partners#returns"`
**And** в нём канал поддержки: телефон ссылкой `tel:+79682732168` с подписью `+7 968 273-21-68` и почта ссылкой `mailto:info@optisport.ru` с подписью `info@optisport.ru`
**And** ссылки на `/returns` в блоке **нет** — этого адреса не существует

**Given** страница корзины (`/cart`) с непустой корзиной
**When** она отображается
**Then** тот же блок `data-testid="returns-support-notice"` присутствует внутри `data-testid="cart-summary"`, рядом с кнопкой «Перейти к оформлению»
**And** это **один и тот же** компонент, а не две копии разметки

### AC2 (FR-41-15) — якорь на условия возврата существует

**Given** страница `/partners`
**When** она отображается
**Then** секция «Рекламации и возвраты» (`partners/page.tsx:154-175`) несёт `id="returns"`
**And** переход по `/partners#returns` прокручивает страницу к этой секции
**And** остальной контент и разметка страницы не меняются

### AC3 (FR-41-20) — ссылка на политику ПДн в блоке оформления заказа

**Given** страница оформления заказа с непустой корзиной
**When** отображается блок сводки заказа
**Then** строка под кнопкой подтверждения читается дословно: `Нажимая кнопку, вы соглашаетесь с условиями обработки персональных данных в соответствии с «Политикой обработки персональных данных»`
**And** фрагмент `«Политикой обработки персональных данных»` — ссылка на `/privacy-policy` с `target="_blank"` и `rel="noopener noreferrer"` (паттерн `SubscribeForm.tsx:172-179`)
**And** чекбокс согласия в форме заказа **не** добавляется — ни обязательный, ни опциональный
**And** в корзине (`/cart`) эта строка **не** дублируется: FR-41-20 относится к оформлению заказа

### AC4 (FR-41-18) — русскоязычные плейсхолдеры без `example` и `XXXXXXXXXX`

**Given** форма оформления заказа
**When** пользователь видит поля и сообщения валидации
**Then** плейсхолдер поля «Электронная почта» — `pochta@mail.ru` (было `example@mail.com`)
**And** подсказка поля «Телефон» — `Формат: +7 и 10 цифр номера` (было `Формат: +7XXXXXXXXXX`)
**And** сообщение об ошибке телефона в `checkoutSchema.ts:16` — `Формат: +7 и 10 цифр номера (например, +79001234567)`
**And** `grep -rn "example\|XXXXXXXXXX" frontend/src/components/checkout/ frontend/src/schemas/checkoutSchema.ts` не находит ни одного вхождения вне тестов
**And** регулярка валидации `/^\+7\d{10}$/` и поведение формы **не** меняются — правится только текст

### AC5 (FR-41-16) — сумма и состав видны до подтверждения (регрессионное закрепление)

**Given** страница оформления заказа с непустой корзиной
**When** она отображается
**Then** внутри одного блока `data-testid="order-summary"` присутствуют одновременно: список товаров (`data-testid="order-summary-items"`), итоговая сумма (`data-testid="total-price"`) и кнопка подтверждения (`data-testid="checkout-submit-button"`)
**And** сумма выводится с символом валюты `₽`
**And** это поведение закреплено тестом — сейчас оно верно, но ничем не защищено

### AC6 (FR-41-16) — пустая корзина не показывает нулевой итог

**Given** корзина пуста
**When** пользователь открывает `/checkout`
**Then** в блоке сводки отображается `Корзина пуста` (`data-testid="empty-cart-message"`)
**And** ни `data-testid="total-price"`, ни `data-testid="total-price-items"` в DOM **отсутствуют** — нулевая сумма как итог заказа не показывается
**And** кнопка подтверждения отсутствует
**And** блок `returns-support-notice` в этом состоянии не показывается: он привязан к оплате, а оплаты нет

### AC7 (FR-41-15, находка вне аудита) — подвал больше не ведёт на 404

**Given** подвал темы blue (`Footer.tsx`, колонка «Информация»)
**When** он отображается
**Then** пункт «Возврат» ведёт на `/partners#returns`, а не на несуществующий `/returns`
**And** `Footer.test.tsx:72` приведён к новому адресу
**And** остальные двенадцать адресов подвала не трогаются
**And** запись про `/returns` в `deferred-work.md:759-761` помечена закрытой стори 41.4

### AC8 (NFR-41-06) — доступность

**Given** новый блок торговой информации
**When** проверяется доступность
**Then** блок обёрнут в `<section aria-label="Условия возврата и поддержка">`
**And** все три ссылки достижимы с клавиатуры и имеют осмысленное доступное имя (не «здесь», не «подробнее»)
**And** `axe` не находит нарушений на `CartSummary` и на новом компоненте — проверка добавляется в `frontend/src/components/cart/__tests__/accessibility.test.tsx` по образцу строк 13-25

### AC9 (границы) — что стори НЕ делает

**Then** **не** добавляется чекбокс согласия в форму заказа (см. AC3)
**And** **не** трогается бэкенд: `openapi.yaml`, `frontend/src/types/api.generated.ts`, сериализаторы, `UserConsent`, миграции — контракт API не меняется, `npm run generate:types` не запускается
**And** **не** правится `PasswordResetRequestForm.tsx:77` (`example@email.com`) — FR-41-18 ограничен интерфейсом оформления заказа; вынести в `deferred-work.md`
**And** **не** мигрируются на новую константу контактов существующие места хардкода (`Footer.tsx:76-77`, `ElectricFooter.tsx:112-124`, `delivery/page.tsx:44-45`) — константа заводится и используется **только** новым кодом, миграция подвалов уходит в `deferred-work.md`
**And** **не** заводится маршрут `/returns` и CMS-страница под него — решение владельца: указывать на существующий раздел `/partners`
**And** **не** трогается `ElectricFooter.tsx` — в теме electric пункт называется «Возврат товара» и ссылкой не является (`ElectricFooter.tsx:81` — строка в массиве текста)
**And** **не** меняется логика расчёта сумм, промокодов и гидратации в `CartSummary`/`OrderSummary`

## Tasks / Subtasks

- [x] **Task 1. Ветка и baseline**
  - [x] `git switch -c feature/story-41-4-checkout-trade-info` от `develop` (прямые коммиты в `develop` запрещены)
  - [x] `git rev-parse --short HEAD` → сверить с `baseline_commit: 87b00945`; при расхождении перечитать координаты в Dev Notes перед правкой

- [x] **Task 2. Константы контактов** (AC1)
  - [x] Создать `frontend/src/constants/contacts.ts`:
        ```ts
        /** Единая точка правды для контактов поддержки в новом коде. */
        export const SUPPORT_PHONE_DISPLAY = '+7 968 273-21-68';
        export const SUPPORT_PHONE_HREF = 'tel:+79682732168';
        export const SUPPORT_EMAIL = 'info@optisport.ru';
        ```
  - [x] Значения взять **дословно** из `Footer.tsx:76-77` — они уже отребрендены на OPTISPORT
  - [x] Существующие хардкоды не трогать (AC9)

- [x] **Task 3. Компонент `ReturnsAndSupportNotice`** (AC1, AC8)
  - [x] Создать `frontend/src/components/common/ReturnsAndSupportNotice.tsx`
  - [x] Директива `'use client'` **не нужна** — компонент без состояния и обработчиков; `next/link` работает в Server Component. Но он рендерится внутри клиентских `CartSummary`/`OrderSummary`, поэтому фактически исполнится на клиенте — это нормально и директивы не требует
  - [x] Разметка (структура обязательна, классы — на усмотрение):
        ```tsx
        <section aria-label="Условия возврата и поддержка" data-testid="returns-support-notice">
          <p>
            <Link href="/partners#returns">Условия возврата и рекламаций</Link>
          </p>
          <p>
            Поддержка: <a href={SUPPORT_PHONE_HREF}>{SUPPORT_PHONE_DISPLAY}</a>,{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
          </p>
        </section>
        ```
  - [x] **Оформление разное в двух местах** — `CartSummary` использует CSS-переменные темы blue (`text-[var(--color-text-secondary)]`, `text-body-s`), `OrderSummary` — палитру Tailwind (`text-xs text-gray-500`). Поэтому компонент принимает `className?: string` и не задаёт собственный цвет текста; типографику каждый вызывающий передаёт сам
  - [x] Ссылка на `/partners#returns` — через `next/link` (`Link`); `tel:`/`mailto:` — обычные `<a>`: `next/link` для внешних схем не нужен
  - [x] Экспортировать из `frontend/src/components/common/index.ts` вместе с типом пропсов (образец — `ProductBadge` в том же файле)
  - [x] Комментарии и docstring — на русском (NFR-41-03)

- [x] **Task 4. Якорь на `/partners`** (AC2)
  - [x] `frontend/src/app/(blue)/partners/page.tsx:155` — добавить `id="returns"` элементу `<section className="mb-16">`, который открывает раздел «Рекламации и возвраты» (комментарий-маркер на строке 154, заголовок 156-158)
  - [x] Больше на этой странице ничего не менять; якорей `id` в файле сейчас нет ни одного — этот будет первым
  - [x] Проверить вручную: `/partners#returns` прокручивает к разделу

- [x] **Task 5. `OrderSummary` — блок торговой информации и ссылка на политику** (AC1, AC3, AC5, AC6)
  - [x] `frontend/src/components/checkout/OrderSummary.tsx`. Блок `{!isEmpty && (...)}` — строки 120-140: сюда, **после** `<Button>` (133) и рядом с абзацем 136-138, вставить `<ReturnsAndSupportNotice />`
  - [x] Оставить блок внутри условия `!isEmpty` — при пустой корзине он не показывается (AC6)
  - [x] Абзац строки 136-138 переписать: текст `Нажимая кнопку, вы соглашаетесь с условиями обработки персональных данных в соответствии с` + `<Link href="/privacy-policy" target="_blank" rel="noopener noreferrer">«Политикой обработки персональных данных»</Link>`
  - [x] Импортировать `Link` из `next/link` — сейчас его в файле нет
  - [x] **Ничего не менять** в расчёте сумм, в `isEmpty` (строка 37) и в списке товаров: AC5/AC6 описывают уже работающее поведение и закрепляются тестами, а не переписыванием
  - [x] Обновить docstring компонента (строки 16-31): добавить упоминание Story 41.4 и нового блока

- [x] **Task 6. `CartSummary` — блок торговой информации** (AC1)
  - [x] `frontend/src/components/cart/CartSummary.tsx`: вставить `<ReturnsAndSupportNotice />` **после** блока условного рендеринга кнопки (строки 84-111), внутри корневого `div` c `data-testid="cart-summary"`
  - [x] Показывать **всегда**, когда `CartSummary` смонтирован: при пустой корзине рендерится `EmptyCart` (`CartPage.tsx:58-60`) и `CartSummary` на экран вообще не попадает, так что отдельного условия не нужно
  - [x] Ссылку на политику ПДн здесь **не** добавлять (AC3)
  - [x] Типографику передать через `className` в стиле темы blue: `text-body-s text-[var(--color-text-secondary)]`
  - [x] Не трогать `mounted`-паттерн, `formatPrice`, `PromoCodeInput` и `data-testid="checkout-button"`

- [x] **Task 7. Плейсхолдеры** (AC4)
  - [x] `frontend/src/components/checkout/ContactSection.tsx:44` → `placeholder="pochta@mail.ru"`
  - [x] `frontend/src/components/checkout/ContactSection.tsx:65` → `helper="Формат: +7 и 10 цифр номера"`
  - [x] `frontend/src/components/checkout/ContactSection.tsx:18` — комментарий в docstring «формат +7XXXXXXXXXX» привести к новой формулировке (тоже видимая строка `XXXXXXXXXX` в коде, хоть и в комментарии)
  - [x] `frontend/src/schemas/checkoutSchema.ts:16` → сообщение `'Формат: +7 и 10 цифр номера (например, +79001234567)'`; регулярку `/^\+7\d{10}$/` **не** трогать
  - [x] `placeholder="+79001234567"` (строка 63) оставить как есть — это конкретный образец, а не `XXXX`
  - [x] Проверка: `cd frontend && grep -rn "example\|XXXXXXXXXX" src/components/checkout src/schemas/checkoutSchema.ts` → пусто (кроме `__tests__/`, которые правятся в Task 9)

- [x] **Task 8. Подвал: `/returns` → `/partners#returns`** (AC7)
  - [x] `frontend/src/components/layout/Footer.tsx:70` — `{ label: 'Возврат', href: '/returns' }` → `href: '/partners#returns'`
  - [x] `frontend/src/components/layout/__tests__/Footer.test.tsx:72` — ожидание `href` привести к `/partners#returns`
  - [x] `ElectricFooter.tsx` **не** трогать (AC9)
  - [x] В `_bmad-output/implementation-artifacts/deferred-work.md` (запись `spec-footer-links-oferta`, строки 759-761) дописать пометку о закрытии стори 41.4

- [x] **Task 9. Тесты** (AC1-AC8, NFR-41-01)
  - [x] **Сначала** прогнать затрагиваемые файлы на неизменённом коде и зафиксировать число зелёных: `cd frontend && npm run test -- src/components/checkout src/components/cart src/components/layout/__tests__/Footer.test.tsx`
  - [x] Правка сломанных: `ContactSection.test.tsx:122` и комментарий `:134`; `CheckoutForm.test.tsx:210` — регулярка `/Формат: \+7XXXXXXXXXX/` → `/Формат: \+7 и 10 цифр номера/`
  - [x] Правка `Footer.test.tsx:72` (Task 8)
  - [x] Новый `frontend/src/components/common/__tests__/ReturnsAndSupportNotice.test.tsx`: ссылка на `/partners#returns` с точным доступным именем; `tel:`/`mailto:` присутствуют; `aria-label` секции; отсутствие подстроки `/returns` в `href` любой ссылки
  - [x] `CartSummary.test.tsx`: блок `returns-support-notice` присутствует; ссылка на политику ПДн в корзине **отсутствует** (AC3)
  - [x] `CheckoutForm.test.tsx` (или новый `OrderSummary.test.tsx` — отдельного файла для `OrderSummary` сейчас нет): AC3 — точный текст строки согласия и `href="/privacy-policy"` с `target="_blank"`; AC5 — состав + итог + кнопка внутри одного `order-summary`; AC6 — при пустой корзине `total-price` и `total-price-items` отсутствуют, `returns-support-notice` отсутствует
  - [x] `frontend/src/components/cart/__tests__/accessibility.test.tsx`: axe на `CartSummary` с новым блоком (AC8)
  - [x] Прогон: `cd frontend && npm run test`, `npm run lint`, `npx tsc --noEmit`
  - [x] Backend не прогонять — код бэкенда не менялся

- [x] **Task 10. Ручная проверка** (AC1-AC7)
  - [x] `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`
  - [x] `/cart` с товарами: блок возврата и поддержки под кнопкой; клик по «Условия возврата и рекламаций» → `/partners`, страница прокручена к разделу «Рекламации и возвраты»
  - [x] `/checkout` с товарами: состав, итог и кнопка в одном блоке; блок возврата и поддержки на месте; ссылка на политику открывается в новой вкладке
  - [x] `/checkout` с пустой корзиной: «Корзина пуста», нулевого итога и блока возврата нет
  - [x] Подвал: «Возврат» → `/partners#returns`, а не 404
  - [x] Поля формы: `pochta@mail.ru`, подсказка телефона без `XXXXXXXXXX`; ввести `1234567890` → сообщение об ошибке тоже без `XXXXXXXXXX`
  - [x] Клавиатура: Tab по новым ссылкам, видимый фокус, Enter открывает

- [x] **Task 11. Перед коммитом**
  - [x] `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` — убедиться, что затронуты только ожидаемые символы
  - [x] `File List` сверять с `git diff --name-only 87b00945..HEAD`, а не с памятью (находка ревью в 41.0 и 41.5 — дважды)
  - [x] Установить `review_head` в frontmatter на коммит, завершающий содержательную работу
  - [x] Коммит и push — только по явной просьбе владельца

### Review Findings

Проверка 2026-09-05: диапазон `87b00945..d0772737`, AC1–AC9; три независимых прохода с последующей проверкой находок основным агентом. Статусы Story и tracker пока не изменены, исправления реализации не применялись.

- [x] [Review][Patch][P2] Сохранить заполненную форму при чтении условий возврата через одноразовый in-memory `checkoutDraft` — владелец выбрал этот вариант 2026-09-05. Текущее рабочее дерево уже реализует сохранение перед переходом в текущей вкладке и восстановление после Back; решение требуется закрепить тестами и включить в changeset. [frontend/src/components/common/ReturnsAndSupportNotice.tsx:40; frontend/src/components/checkout/CheckoutForm.tsx:73-115,305-319; frontend/src/utils/checkout/checkoutDraft.ts:1-35]
- [x] [Review][Patch][P3] Согласовать метаданные changeset — `review_head` пуст при отмеченной выполненной Task 11; утверждение «коммитов нет» устарело после `d0772737`. Закрепить проверяемую границу после завершения текущей доработки, актуализировать пояснение и включить в File List изменения счётчиков GitNexus в `AGENTS.md` и `CLAUDE.md`, `CheckoutForm.tsx` и новый `checkoutDraft.ts`. [_bmad-output/implementation-artifacts/Story/41-4-checkout-trade-info-and-policy-link.md:3,209-213,339-366]
- [x] [Review][Patch][P2] Добавить регрессионные тесты механизма черновика — текущие 51 целевых тестов проходят, но ни один не кликает `/partners#returns`, не проверяет восстановление всех полей/выбранного адреса/флага сохранения и очистку при смене пользователя или успешном заказе. Поломка `readCheckoutDraft`/`saveCheckoutDraft` останется незамеченной, поэтому исправление исходного P2 пока не защищено. [frontend/src/components/checkout/CheckoutForm.tsx:73-115,305-319; frontend/src/utils/checkout/checkoutDraft.ts:15-35]
- [x] [Review][Defer][P2] Холодный вход `/partners#returns` не прокручивает к условиям — существующая проблема, уже описанная в deferred-work; новый browser-check подтвердил `scrollY=0`, координату секции `y=1186`. При клике внутри приложения секция находится на `y=96`, `scrollY=1090`. AC2 подтверждён только для перехода внутри приложения, не для холодного входа. Исправление не применялось. [frontend/src/providers/AuthProvider.tsx; _bmad-output/implementation-artifacts/deferred-work.md, раздел стори 41.4]

Проверки текущего review: целевой Vitest — **19 файлов, 380 passed, 4 skipped**, exit 0; ESLint изменённых production-файлов — exit 0; `npx tsc --noEmit --incremental false` — exit 0. В тестах есть предупреждения React `act(...)`; полный frontend suite в этом review не запускался. GitNexus: `detect-changes --scope compare --base-ref 87b00945` — 21 файл, 14 символов, 2 процесса, MEDIUM; impact `OrderSummary`, `ContactSection`, `CartSummary`, `PartnersPage` — LOW. Ограничение независимости Blind Hunter: при первом чтении общего diff ему также попал текст Story; дальнейший анализ выполнен по коду, находка независимо воспроизведена основным агентом.

## Dev Notes

### Что здесь уже работает и переписывать это не надо

FR-41-16 («итоговая сумма и состав явно видны до подтверждения оплаты») **на момент baseline выполнен**. `OrderSummary.tsx` рендерит внутри одного контейнера: список товаров с ценой за штуку и суммой позиции (53-74), «Итого за товары» (78-83), «Итого» (92-98) и кнопку «Оформить заказ» (122-133). На desktop блок `lg:sticky lg:top-4` (41), на мобильном идёт под формой — прокрутки к другому блоку не требуется ни там, ни там.

Дефекта нет — есть **незащищённость**: ни один тест не проверяет, что состав, итог и кнопка живут в одном блоке, и ни один не проверяет, что при пустой корзине нулевой итог не показывается. AC5 и AC6 закрывают эту дыру тестами. Переписывать разметку не нужно и вредно.

### Почему `/partners`, а не `/oferta`

| Документ | Что в нём есть | Годится под ЗоЗПП? |
|---|---|---|
| `/oferta` (CMS, slug `oferta`) | Претензионный порядок, п. 8, срок ответа 10 дней. Слов «возврат» и «обмен» — **ноль** | Нет |
| `/partners:154-175` | Порядок при недовложении и пересортице (акт, фото, 24 часа), рекламации по качеству 14 дней при сохранении товарного вида | **Да** |
| `/returns` | Не существует: ни маршрута, ни CMS-слага | Нет, это 404 |

Текст AC в эпике (`/oferta`) написан до прод-верификации 2026-08-30 и опровергнут уточнением к FR-41-15 в том же эпике. Стори следует уточнению.

### Три места хардкода контактов — и почему миграция отложена

`+7 968 273-21-68` / `info@optisport.ru` продублированы в `Footer.tsx:76-77`, `ElectricFooter.tsx:112-124`, `delivery/page.tsx:44-45` и (только почта) `ComingSoonClient.tsx:114`. Новый блок стал бы пятой копией — поэтому заводится `constants/contacts.ts`. Миграция существующих четырёх в объём **не берётся**: каждая живёт в своей теме со своей разметкой, правка тянет за собой тесты подвалов, а к торговой информации при оплате отношения не имеет. Уходит в `deferred-work.md`.

### Тесты: что сломается и что нет

| Файл | Как ищет | Ломается? |
|---|---|---|
| `ContactSection.test.tsx:122` | `getByText(/Формат: \+7XXXXXXXXXX/)` | **Да** — правка обязательна |
| `ContactSection.test.tsx:134` | комментарий с той же строкой | Комментарий, но привести к новому тексту |
| `CheckoutForm.test.tsx:210` | `getByText(/Формат: \+7XXXXXXXXXX/)` | **Да** — правка обязательна |
| `Footer.test.tsx:72` | `toHaveAttribute('href', '/returns')` | **Да** — охраняет мёртвый линк |
| `CheckoutForm.test.tsx:298` | `total-price` содержит `200` | Нет — суммы не трогаем |
| `CartSummary.test.tsx:136-149` | заголовки и `checkout-button` | Нет — вставка идёт **после** кнопки |
| `accessibility.test.tsx` (cart) | axe | Не ломается, но дополняется (AC8) |
| backend-тесты | — | Нет — бэкенд не менялся |

Строка `Нажимая кнопку, вы соглашаетесь...` (`OrderSummary.tsx:137`) **не покрыта ни одним тестом** — `grep -rn "Нажимая кнопку" frontend/src` даёт единственное вхождение, в самом компоненте. Её переписывание ничего не роняет, и именно поэтому AC3 требует закрепить новый текст тестом.

### Отдельного `OrderSummary.test.tsx` не существует

В `frontend/src/components/checkout/__tests__/` шесть файлов, `OrderSummary` среди них нет — компонент покрывается косвенно через `CheckoutForm.test.tsx` и `CheckoutForm.integration.test.tsx`. Допустимы оба варианта: добавить проверки в `CheckoutForm.test.tsx` или завести `OrderSummary.test.tsx`. Второй чище (компонент принимает три пропса и читает `cartStore`), но требует своего мока `@/stores/cartStore` — образец мока есть в `CartSummary.test.tsx:22-41`.

### Гидратация: не сломать существующую защиту

`OrderSummary.tsx:37` — `const isEmpty = items.length > 0 ? false : (isCartEmpty ?? true);` — намеренная защита от гидратации: если стор уже наполнен, пропс `isCartEmpty` игнорируется. `CartSummary.tsx:29-37` — тот же класс защиты через `mounted`. Новый блок вставляется **вне** этих выражений и их не касается. Не «упрощать» условия по дороге.

### Доступность блока

Три ссылки подряд — типичное место, где скринридер получает «ссылка, ссылка, ссылка». Поэтому: обёртка `<section aria-label="Условия возврата и поддержка">` даёт группе имя, а доступные имена ссылок берутся из их собственного текста (`Условия возврата и рекламаций`, номер телефона, адрес почты) — они самодостаточны и вне контекста. Никаких «подробнее» и «здесь» (WCAG 2.4.4).

### Окружение

- Правки `frontend/src/` применяются рестартом контейнера: `docker compose --env-file .env -f docker/docker-compose.yml restart frontend`. Пересбор нужен только при изменении зависимостей или `next.config.ts` — здесь ни того, ни другого
- `/cart` и `/checkout` доступны на проде независимо от `ACTIVE_THEME=coming_soon`: тема управляет только редиректом корня (`app/page.tsx:22-31`), а оба адреса перечислены в `KNOWN_TOP_LEVEL_ROUTES` (`middleware.ts:34,36`)
- `/checkout` **не** входит в `protectedPaths` middleware (`middleware.ts:376`) — страницу открывает и аноним, форма собирает ПДн до всякой авторизации. Это дополнительный аргумент за FR-41-20: ссылка на политику нужна ровно там, где данные вводятся
- Ветка от `develop`, прямые коммиты в `develop` запрещены

### Project Structure Notes

- Новый общий компонент → `frontend/src/components/common/` (там уже лежат `ProductBadge`, `RecommendationsRow` — компоненты, используемые несколькими доменами). Класть его в `cart/` или `checkout/` нельзя: он нужен обоим
- Новые константы → `frontend/src/constants/` (рядом с `quickLinks.tsx`, `theme.ts`)
- Тест нового компонента → `frontend/src/components/common/__tests__/` (каталог существует)
- Экспорт через barrel `components/common/index.ts` — принятый в проекте паттерн, импорт вида `import { ReturnsAndSupportNotice } from '@/components/common'`

### References

- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#Story 41.4] — исходные AC (с устаревшей ссылкой на `/oferta`)
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-15] — уточнение 2026-08-30: условия возврата в `/partners`, мёртвая ссылка `/returns` в подвале
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#FR-41-16, FR-41-18, FR-41-20] — торговая информация, плейсхолдеры, ссылка на политику без чекбокса
- [Source: _bmad-output/planning-artifacts/epic-41-site-audit.md#NFR-41-01, NFR-41-03, NFR-41-06] — тесты, русские комментарии, доступность
- [Source: _bmad-output/implementation-artifacts/deferred-work.md:759-761] — запись про мёртвый `/returns` и зелёный тест, её охраняющий
- [Source: _bmad-output/implementation-artifacts/Story/41-3-separate-pdn-and-marketing-consents.md] — паттерн ссылки на политику в метке согласия, дисциплина «сначала прогнать тесты на неизменённом коде»
- [Source: project-context.md#7 Frontend-специфика] — Server vs Client Components, рестарт контейнера, `next/link`
- [Source: frontend/src/components/home/SubscribeForm.tsx:172-179] — эталон ссылки на `/privacy-policy` с `target="_blank" rel="noopener noreferrer"`
- [Source: frontend/src/app/(blue)/partners/page.tsx:154-175] — раздел «Рекламации и возвраты», куда ведёт якорь

## Dev Agent Record

### Agent Model Used

Claude Opus 5 (`claude-opus-5`), workflow `bmad-dev-story`.

### Debug Log References

- Базис до правок (Task 9, первый подпункт): `npm run test -- --run src/components/checkout src/components/cart src/components/layout/__tests__/Footer.test.tsx` → **17 файлов, 359 passed, 4 skipped**.
- Итоговый полный прогон: `npm run test` → **154 файла, 2683 passed, 16 skipped**. `npm run lint` — чисто, `npm run format:check` — чисто, `npx tsc --noEmit` — без ошибок.
- Ручная проверка (Task 10) выполнена не глазами, а браузером: браузерные MCP-инструменты в сессии недоступны, поэтому проверка проведена **временным Playwright-спеком** `tests/e2e/tmp-story-41-4-check.spec.ts` (7 сценариев на AC1-AC8, все зелёные) со скриншотами `/cart`, `/checkout` и `/partners#returns`. Спек и скриншоты после прогона удалены — в объём стори E2E-тесты не входят, файл был инструментом проверки.
- `npx gitnexus detect-changes --scope all` → 18 файлов, 6 символов, risk **medium**, ни одного HIGH/CRITICAL. Затронутые символы ровно ожидаемые: `PartnersPage`, `ContactSection`, `OrderSummary`, `OrderSummaryProps`, `DEFAULT_COLUMNS`, `checkoutSchema`. Процессы: `CheckoutPage`, `PartnersPage`.
**Доработка по итогам ревью (2026-09-05, второй проход)**

- Целевой прогон до правок: `npm run test -- --run src/components/checkout src/components/cart src/components/common src/components/layout/__tests__/Footer.test.tsx` → **20 файлов, 392 passed, 4 skipped**. После добавления тестов черновика (с `src/utils/checkout`) → **22 файла, 412 passed, 4 skipped**.
- Полный прогон фронтенда: `npm run test` → **156 файлов, 2703 passed, 16 skipped**, exit 0. `npm run lint` — exit 0, `npx tsc --noEmit` — exit 0, `npm run format:check` — чисто (после `prettier --write` двух файлов из `52d5392c`, которые в коммит попали неотформатированными).
- **Мутационная проверка новых тестов** — каждая поломка механизма ловится, тесты не декоративные:
  - `readCheckoutDraft` игнорирует `userId` + `saveCheckoutDraft` не копирует `values` → 3 падения в `checkoutDraft.test.ts`;
  - ранний `return` в `onClickCapture` (черновик не пишется) → 6 падений в `CheckoutForm.draft.test.tsx`;
  - убран `...initialDraft?.values` из `defaultValues` (черновик не восстанавливается) → 4 падения;
  - убран `clearCheckoutDraft()` в `onSubmit` (не чистится после заказа) → 1 падение;
  - убран `clearCheckoutDraft()` в `useEffect` монтирования (черновик перестал быть одноразовым) → 1 падение.
- `npx gitnexus detect-changes --scope all --repo "C:\Users\1\DEV\FREESPORT"` → 4 файла, 4 символа, risk **medium**, HIGH/CRITICAL нет. Затронутые символы: `CheckoutFormFields`, `link` (обработчик `onClickCapture`) и счётчики GitNexus в `AGENTS.md`/`CLAUDE.md`. Процессы: `CheckoutPage → ReadCheckoutDraft / SaveCheckoutDraft / ClearCheckoutDraft / SplitFullName`.
- Локальный контейнер frontend **не подхватывает правки через HMR** (bind-mount `../frontend:/app` на Windows не пробрасывает inotify): изменение `scroll-mt-24` стало видно только после `docker compose restart frontend`. После рестарта фронтенда nginx отдаёт 502 на новый IP — лечится `docker compose restart nginx` (см. память `project_prod_nginx_upstream_dns`).

### Completion Notes List

**Что сделано**

- Заведена единая точка правды для контактов поддержки и общий компонент `ReturnsAndSupportNotice`, используемый **одним экземпляром** и в `CartSummary`, и в `OrderSummary` (AC1). Оформление разное — передаётся вызывающим через `className`, собственного цвета текста компонент не задаёт.
- Секция «Рекламации и возвраты» на `/partners` получила `id="returns"` (AC2).
- В `OrderSummary` строка согласия переписана дословно по AC3, фрагмент «Политикой обработки персональных данных» стал ссылкой на `/privacy-policy` с `target="_blank" rel="noopener noreferrer"`. Чекбокс не добавлялся.
- Три плейсхолдера-нарушителя убраны (AC4), регулярка `/^\+7\d{10}$/` не тронута.
- Подвал ведёт на `/partners#returns` (AC7), тест приведён к новому адресу, записи в `deferred-work.md` помечены закрытыми.
- Тесты: новый `ReturnsAndSupportNotice.test.tsx` (5), новый `OrderSummary.test.tsx` (9, закрывает AC3/AC5/AC6/AC1), блок в `CartSummary.test.tsx` (4, включая проверку **отсутствия** ссылки на политику в корзине), axe и проверка доступных имён в `cart/__tests__/accessibility.test.tsx` (3).

**Закрытие находок ревью (2026-09-05)**

✅ **[P2] Черновик формы при переходе к условиям возврата.** Механизм (`utils/checkout/checkoutDraft.ts` + `onClickCapture` на форме + `initialDraft` в `defaultValues`) реализован коммитом `52d5392c` и теперь **закреплён тестами**, а не только рабочим деревом. Почему именно так: ссылка «Условия возврата и рекламаций» уходит в той же вкладке, и без черновика Back стирал бы всё введённое. Хранилище — модульная переменная, не `localStorage` и не `sessionStorage`: ПДн покупателя не должны переживать вкладку. Черновик одноразовый (стирается в `useEffect` монтирования) и привязан к `userId`, а подписка на `authStore` стирает его при входе/выходе — черновик одного пользователя не может попасть в форму другого.

✅ **[P2] Регрессионные тесты механизма.** 20 новых тестов в двух файлах:
- `src/utils/checkout/__tests__/checkoutDraft.test.ts` (10) — чтение/запись/очистка, изоляция по `userId` (включая случай анонима), копирование `values` при сохранении, очистка при смене пользователя и при выходе, отсутствие ложной очистки при изменении постороннего поля стора.
- `src/components/checkout/__tests__/CheckoutForm.draft.test.tsx` (10) — клик именно по `/partners#returns` внутри формы, сохранение незавершённого ввода, восстановление всех девяти полей, восстановление выбранного адреса (`aria-checked`) и флага «Запомнить этот адрес в профиле», одноразовость (третий заход даёт чистую форму), приоритет восстановленного ввода над автозаполнением default-адреса, отсутствие записи при Ctrl-клике и клике средней кнопкой, отсутствие записи при клике по ссылке на политику ПДн, изоляция черновика анонима от авторизованного пользователя, очистка после успешного заказа.

Все 20 проверены мутациями (см. Debug Log): каждая поломка механизма роняет тесты.

✅ **[P3] Метаданные changeset.** `review_head` установлен, File List приведён к `git diff --name-only`, утверждение «коммитов нет» заменено фактическим составом коммитов. Заодно `prettier --write` привёл `CheckoutForm.tsx` и `checkoutDraft.ts` к стилю проекта — в `52d5392c` они попали неотформатированными, `format:check` на них падал.

**Отклонения от текста задач — сознательные, с обоснованием**

1. **Константы легли в `frontend/src/config/contacts.ts`, а не в `frontend/src/constants/contacts.ts`.** Каталога `src/constants/` в проекте нет; `quickLinks.tsx` и `theme.ts`, рядом с которыми задача велела класть файл, лежат в `src/config/`. Заводить второй каталог того же назначения ради одного файла хуже, чем следовать фактической структуре. На AC это не влияет — путь константы ни в одном AC не упомянут.
2. **Секции `#returns` добавлен ещё и `scroll-mt-24`.** Без него якорь формально срабатывал, но заголовок «Рекламации и возвраты» уезжал под липкую шапку (замер в браузере: `headingY < высоты header`). Это правка того же элемента, что и якорь, и без неё AC2 выполняется только на бумаге.
3. **В `deferred-work.md` закрыты две записи про `/returns`, а не одна.** Задача называла только `spec-footer-links-oferta` (строки 759-761), но тот же дефект вторично записан в разделе «прод-верификация стори 41.5». Оставлять дубль открытым после починки — вводить в заблуждение следующего читателя.

**Находка, требующая решения владельца (в объём не бралась, записана в `deferred-work.md`)**

⚠️ **Якоря `#fragment` не работают при холодной загрузке адреса — по всему сайту, а не только на `/partners`.** Проверено на продакшен-сборке (`next build` + `next start`): `GET /partners` отдаёт HTML **без единого тега `<section>`** — вся разметка приезжает RSC-пейлоадом и вставляется после гидратации, поэтому в момент обработки фрагмента браузером цели `#returns` в документе ещё нет (`scrollY = 0` при `headingY = 1186`). Дефект **предсуществует** стори 41.4: `/delivery#pickup` из подвала, заведённый задолго до неё, ведёт себя ровно так же. Путь, который строит эта стори — клик по ссылке из блока и из подвала — работает и прокручивает к разделу (проверено в браузере). Ломается только вход по вставленному или сохранённому в закладки адресу с якорем.

**Не сделано осознанно (AC9)**

Бэкенд не тронут, `npm run generate:types` не запускался, чекбокс согласия не добавлен, `PasswordResetRequestForm.tsx` и четыре места хардкода контактов не мигрированы (вынесено в `deferred-work.md`), `ElectricFooter.tsx` не тронут, маршрут `/returns` не заводился, логика сумм и гидратации не менялась.

**`review_head` установлен.** Содержательная работа стори — три коммита: `d0772737` (торговая информация и ссылка на политику), `52d5392c` (черновик формы при переходе к условиям возврата) и коммит доработки по ревью, на который и указывает `review_head`. Документационная правка метаданных идёт отдельным коммитом **после** `review_head` и границу приёмки не сдвигает — по правилу из шапки файла. Коммиты и push сделаны по явному разрешению Alex 2026-09-05.

### File List

**Новые файлы**

- `frontend/src/config/contacts.ts`
- `frontend/src/components/common/ReturnsAndSupportNotice.tsx`
- `frontend/src/components/common/__tests__/ReturnsAndSupportNotice.test.tsx`
- `frontend/src/components/checkout/__tests__/OrderSummary.test.tsx`
- `frontend/src/utils/checkout/checkoutDraft.ts`
- `frontend/src/utils/checkout/__tests__/checkoutDraft.test.ts`
- `frontend/src/components/checkout/__tests__/CheckoutForm.draft.test.tsx`
- `_bmad-output/implementation-artifacts/Story/41-4-checkout-trade-info-and-policy-link.md` (сам файл стори)

**Изменённые файлы**

- `frontend/src/app/(blue)/partners/page.tsx`
- `frontend/src/components/cart/CartSummary.tsx`
- `frontend/src/components/checkout/OrderSummary.tsx`
- `frontend/src/components/checkout/ContactSection.tsx`
- `frontend/src/components/checkout/CheckoutForm.tsx`
- `frontend/src/components/layout/Footer.tsx`
- `frontend/src/components/common/index.ts`
- `frontend/src/schemas/checkoutSchema.ts`
- `frontend/src/components/cart/__tests__/CartSummary.test.tsx`
- `frontend/src/components/cart/__tests__/accessibility.test.tsx`
- `frontend/src/components/checkout/__tests__/CheckoutForm.test.tsx`
- `frontend/src/components/checkout/__tests__/ContactSection.test.tsx`
- `frontend/src/components/layout/__tests__/Footer.test.tsx`
- `AGENTS.md`, `CLAUDE.md` — счётчики символов GitNexus, перезаписанные `npx gitnexus analyze` при проверке blast radius (9623 → 9632 символов, 15837 → 15860 связей)
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

Список сверен с `git diff --name-only 87b00945..HEAD` плюс некоммитнутое из `git status --short`, а не с памятью.

## Change Log

| Дата | Изменение |
|---|---|
| 2026-09-05 | Закрыты находки ревью — 3 пункта (2×P2, 1×P3): механизм черновика формы заказа закреплён 20 регрессионными тестами (`checkoutDraft.test.ts`, `CheckoutForm.draft.test.tsx`), каждый проверен мутацией; `review_head` установлен на `99358186`, File List сверен с `git diff --name-only`. Полный прогон фронтенда зелёный (156 файлов, 2703 passed). Статус: in-progress → review. |
| 2026-09-05 | Реализованы AC1-AC9 стори 41.4: общий блок условий возврата и поддержки в корзине и оформлении заказа, якорь `#returns` на `/partners`, ссылка на политику ПДн в сводке заказа, русскоязычные плейсхолдеры, починка мёртвой ссылки подвала. Добавлен 21 тест, полный прогон фронтенда зелёный (2683 passed). Статус: ready-for-dev → review. |
