# Intent: одна подпись у чекбокса — декоративный квадрат перестаёт быть `<label>`

**Источник:** отчёт сканера от 28.09.2026 — `tmp/audit-2026-09-28-extracted.txt`, блок «Внешние сервисы и реклама», проверка «Согласие на рассылку»: «Отдельное согласие на рассылку не найдено» на `/home` (форма подписки) и `/register`. Сверка с продом: `tmp/audit-2026-09-28-verification-2026-10-01.md`.
**Проверено:** по коду `develop` = `4615b8ce` и серверному HTML `/home` прода 01.10.2026 (`User-Agent: AuditikBot/1.0`).
**Исполнитель:** `bmad-quick-dev`. Тип — bugfix, фронтенд, размер S. Решений владельца не требует.
**Вне задачи:** тексты согласий, их порядок и валидация; `ElectricCheckbox` (обёрточный `<label>`, одна подпись); `Toggle`, `AddressModal`, `ElectricSidebar`; дата редакции политики и счётчик Метрики (шаги владельца).

## Проблема

Отдельный неотмеченный чекбокс согласия на рассылку на сайте есть: `pdp_consent` и `marketing_consent` в форме подписки `/home`, в `/register` и `/b2b-register`. Но у каждого такого `input` два `<label for>`:

1. **Первый — пустой.** Это декоративный квадрат `Checkbox`: `<label htmlFor={checkboxId}>` без текста (`components/ui/Checkbox/Checkbox.tsx:46-78`).
2. **Второй — текст согласия.** Это `<label htmlFor>` в самой форме, например `components/home/SubscribeForm.tsx:291-298`.

Фрагмент серверного HTML `/home` с прода:

```html
<input id="…-subscribe-marketing-consent" type="checkbox" aria-labelledby="…-label …-link" name="marketing_consent"/>
<label for="…-subscribe-marketing-consent"></label>          <!-- квадрат, пустой -->
…
<label id="…-label" for="…-subscribe-marketing-consent">Я даю согласие на получение информационных и рекламных рассылок…</label>
```

Скринридер и тесты читают `aria-labelledby`, поэтому для них имя чекбокса верное. Простой анализатор HTML берёт первую подпись (`input.labels[0]`, первый `label[for=id]`) или текст родителя, а там пусто. Выходит, что текст о рассылке в форме есть, а подписанного им чекбокса нет. Это совпадает с формулировкой замечания: сканер выводит весь текст формы и пишет «отдельное согласие не найдено».

**Это гипотеза:** код сканера закрыт. Правка оправдана и без неё: пустой `<label>` и две подписи у одного поля — дефект разметки. Подтвердит или опровергнет гипотезу только следующий прогон сканера.

То же устройство у квадрата в `ElectricConsentCheckbox` (`components/home/ElectricSubscribeForm.tsx:149-166`, тема `/electric`). Там квадрат после отметки содержит «✓», то есть первая подпись — галочка.

## Требуемое поведение

- У каждого `input type="checkbox"`, который рендерят `Checkbox` и `ElectricConsentCheckbox`, ровно одна связанная подпись (`input.labels.length`): текст рядом с чекбоксом. Если у `Checkbox` нет пропса `label` и внешнего `<label for>`, подписей ноль.
- Клик по квадрату по-прежнему ставит и снимает галочку. Внешний вид, hover, focus-ring, disabled, indeterminate и анимация не меняются.
- Работа с клавиатуры и доступное имя чекбоксов не меняются.
- Связка с `react-hook-form` (`register`, неуправляемый режим) работает как раньше.

## Правки

Перед правкой выполни `npx gitnexus impact Checkbox --direction upstream -r "C:\Users\1\DEV\FREESPORT"` и сообщи blast radius (AGENTS.md, раздел GitNexus). По имени `Checkbox` impact возвращает `ambiguous` (функция, константа, папка). Тогда бери граф:

```bash
npx gitnexus cypher "MATCH (a)-[r]->(b) WHERE b.filePath = 'frontend/src/components/ui/Checkbox/Checkbox.tsx' AND a.filePath <> b.filePath RETURN DISTINCT a.filePath, r.type" -r "C:\Users\1\DEV\FREESPORT"
```

На 01.10.2026 потребителей шесть, все передают либо `label`, либо внешний `<label for>` + `aria-labelledby`:

| Потребитель | Как подписан |
|---|---|
| `home/SubscribeForm.tsx` (2 чекбокса) | внешний `<label for>` + `aria-labelledby` |
| `auth/RegisterForm.tsx` (2) | то же |
| `auth/B2BRegisterForm.tsx` (2) | то же |
| `app/(blue)/catalog/CatalogPageClient.tsx` (3) | пропс `label` |
| `business/SidebarFilters/SidebarFilters.tsx` (2) | пропс `label` |
| `checkout/AddressSection.tsx` (1) | пропс `label` |

Потребителей менять не нужно — правка внутри двух компонентов.

### 1. `components/ui/Checkbox/Checkbox.tsx`

Квадрат становится `<span aria-hidden="true">`. Кликабельность даёт сам нативный `input`, растянутый прозрачным слоем поверх квадрата:

- `input`: класс `sr-only peer` → `peer absolute inset-0 z-10 m-0 h-5 w-5 cursor-pointer opacity-0 disabled:cursor-not-allowed`. `input` остаётся первым в контейнере, иначе перестанут работать `peer-*` классы квадрата и иконок.
- Квадрат: `<label htmlFor={checkboxId} className={…}/>` → `<span aria-hidden="true" className={…}/>`. Набор классов тот же, включая `peer-focus:*`, `peer-checked:*`, `peer-hover:*`, `indeterminate`, `disabled`, `motion-reduce` и `className` от вызывающего. Убрать только `cursor-pointer`: курсор теперь задаёт `input`.
- Иконки `Check`/`Minus` не трогать: они уже `pointer-events-none` и `aria-hidden`.
- Текстовая подпись `{label && <label htmlFor={checkboxId}>…}` остаётся как есть — это единственный `<label>`.
- Обновить комментарий над иконками (`:80-83`): клик теперь попадает в прозрачный `input`, а не в `<label>`.

**Почему так, а не просто `<span>` вместо `<label>`.** Если оставить `input` с `sr-only`, клик по квадрату перестанет ставить галочку — это регрессия UX форм согласия и фильтров каталога. Прозрачный нативный `input` поверх кастомного квадрата — стандартный приём: клик, клавиатура и `react-hook-form` работают без JS-обработчиков.

**Проверь `outline`.** Сейчас фокус рисует `peer-focus:ring-*` на квадрате. У прозрачного `input` браузер может нарисовать собственный outline — он не виден из-за `opacity-0`, но убедись в этом в Chrome при навигации Tab.

### 2. `components/home/ElectricSubscribeForm.tsx` — `ElectricConsentCheckbox`

Та же правка в локальном компоненте (`:131-166`):

- `input`: `sr-only peer` → `peer absolute inset-0 z-10 m-0 h-5 w-5 cursor-pointer opacity-0 disabled:cursor-not-allowed`. Квадрат скошен (`-skew-x-12`); прозрачный прямоугольный `input` 20×20 поверх него допустим — зона клика станет чуть шире краёв ромба.
- Квадрат: `<label htmlFor={id}>` → `<span aria-hidden="true">`, классы прежние, `cursor-pointer` убрать. «✓» внутри остаётся (`aria-hidden` у него уже есть).
- Обновить JSDoc над компонентом (`:113-115`): причина `aria-labelledby` — ссылка внутри текста, а не галочка в квадрате.

### 3. Комментарии у потребителей

В `home/SubscribeForm.tsx:283-285` комментарий объясняет `aria-labelledby` тем, что «первый такой label — пустой квадрат `Checkbox`». После правки это неверно. Переписать: `aria-labelledby` нужен, чтобы в имя вошла и ссылка на документ, которая вынесена из `<label>`. В `RegisterForm.tsx` и `B2BRegisterForm.tsx` таких комментариев нет (проверено `grep -n "квадрат"` 01.10.2026). Сами `aria-labelledby` не убирать.

## Тесты

Vitest, рядом с компонентами в `__tests__`.

1. `components/ui/Checkbox/__tests__/Checkbox.test.tsx`:
   - с `label="Test"`: `checkbox.labels` имеет длину 1, её текст — «Test»;
   - без `label`: `checkbox.labels` имеет длину 0;
   - квадрат (`checkbox.nextElementSibling`) — это `SPAN` с `aria-hidden="true"`, а не `LABEL`;
   - `input` не имеет класса `sr-only` и имеет `opacity-0`, `absolute`, `inset-0`;
   - существующие проверки классов квадрата через `nextElementSibling` (`:34`, `:46`, `:56`, `:63`, `:72`) проходят без изменений;
   - `await user.click(screen.getByText('Test'))` переключает чекбокс.
2. `home/__tests__/SubscribeForm.test.tsx`, `auth/__tests__/RegisterForm.test.tsx`, `auth/__tests__/B2BRegisterForm.test.tsx`, `home/__tests__/ElectricSubscribeForm.test.tsx` — новый тест в каждом: у чекбокса ПДн и у чекбокса рассылки `labels.length === 1`; текст подписи рассылки содержит «рассылок», подписи ПДн — «персональных данных». Это прямая проверка того, что видит простой анализатор HTML.
3. Существующие проверки должны пройти без изменений. Обрати внимание:
   - `RegisterForm.test.tsx:100` и `B2BRegisterForm.test.tsx:81` берут `document.querySelector('label[for="…-pdp-consent"]')` и кликают по нему. Сейчас это квадрат, после правки — текстовая подпись; клик по-прежнему ставит галочку. Тест не править;
   - `ElectricSubscribeForm.test.tsx:115-125` («keeps the checkmark glyph out of the accessible name») — оставить, комментарий на `:119` обновить.

## Проверка

Гейты фронтенда, в `frontend/`:

```bash
npm run format:check
npm run lint
npx tsc --noEmit
npm test
```

Серверный HTML на локальном стенде:

```bash
curl -s http://localhost:3000/home | grep -o '<label[^>]*for="[^"]*consent[^"]*"[^>]*>[^<]*' 
```

Ожидается две строки — по одной на чекбокс, обе с текстом согласия. Пустых `<label …></label>` с `for` на consent-поля нет.

В браузере (Chrome, локальный стенд) на `/home` (форма подписки), `/register`, `/b2b-register`, `/electric`, в фильтрах `/catalog` и в чекбоксе «Запомнить этот адрес» на `/checkout`:

- клик по квадрату и по тексту подписи ставит и снимает галочку;
- клик по ссылке в тексте согласия открывает документ и не ставит галочку;
- Tab доводит фокус до чекбокса, виден focus-ring квадрата, второго контура нет, пробел переключает;
- внешний вид в состояниях: пусто, отмечено, ошибка валидации, disabled (во время отправки формы), indeterminate («Все» в категориях каталога) — без изменений;
- форма подписки и регистрация отправляются только при обеих отметках.

## Критерии приёмки

1. У чекбоксов `Checkbox` и `ElectricConsentCheckbox` в серверном и клиентском DOM не больше одного связанного `<label>`, пустых `<label for>` нет.
2. Клик по квадрату переключает чекбокс во всех шести потребителях `Checkbox` и в форме подписки `/electric`.
3. Доступные имена чекбоксов согласия не изменились: существующие тесты на `getByRole('checkbox', { name: … })` зелёные.
4. Новые и существующие тесты зелёные, четыре гейта фронтенда проходят.
5. `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` перед коммитом показывает только `Checkbox`, `ElectricConsentCheckbox` / `ElectricSubscribeForm`, комментарий в `SubscribeForm` и тесты.

**Приёмка на проде (после релиза, шаг владельца):** `curl -s -A "AuditikBot/1.0" https://optisport.ru/home` — у `pdp_consent` и `marketing_consent` по одному `<label for>` с текстом. Следующий прогон сканера: замечание «Согласие на рассылку» должно уйти. Если останется — гипотеза не подтвердилась, а пункт возвращается в принятые исключения. Правку при этом не откатывать.

## Git

Ветка `fix/consent-checkbox-single-label` от `develop`. PR в `develop`, слияние только merge commit (`gh pr merge N --auto --merge`).
