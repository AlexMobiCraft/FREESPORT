# E2E Tests - Оставшиеся проблемы для исправления

**Дата создания:** 2026-01-10
**Текущий статус:** 13 из 39 тестов проходят (33%)
**Цель:** Довести до 35-39 проходящих тестов (90-100%)

---

## 📋 Контекст проекта

### Архитектура
- **Frontend:** Next.js 15.4.6 + TypeScript + React 19 + Tailwind CSS
- **E2E тестирование:** Playwright 1.57.0
- **Окружение:** Frontend запущен в Docker контейнере на порту 3000
- **Рабочая директория:** `C:\Users\38670\.claude-worktrees\FREESPORT\wonderful-noyce`

### Что уже исправлено в предыдущей сессии

#### ✅ Исправление 1: CSS селекторы для полей формы
**Файл:** `frontend/tests/e2e/checkout.spec.ts:190-191`

```typescript
// БЫЛО (некорректный селектор):
await page.fill('#input-кв\\.\/офис', data.apartment);

// СТАЛО:
await page.fill('input[name="apartment"]', data.apartment);
await page.fill('input[name="postalCode"]', data.postalCode);
```

#### ✅ Исправление 2: Strict mode violations для навигации
**Файл:** `frontend/tests/e2e/profile/edit-profile.spec.ts:304-307`

```typescript
// БЫЛО:
await expect(page.locator('a[href="/profile"]')).toBeVisible();

// СТАЛО:
await expect(page.locator('a[href="/profile"]').first()).toBeVisible();
```

#### ✅ Исправление 3: Добавлен data-testid
**Файл:** `frontend/src/components/ui/SearchField/SearchField.tsx:197`

```typescript
return (
  <div ref={containerRef} className="w-full relative" data-testid="search-field">
```

#### ✅ Исправление 4: Отсутствующие page.goto
**Файл:** `frontend/tests/e2e/search-history.spec.ts:181, 366`

```typescript
// Добавлено:
await page.goto('/catalog');
```

#### ✅ Исправление 5: Настройка Playwright для Docker
**Файл:** `frontend/playwright.config.ts:77-84`

```typescript
// Отключен автозапуск локального dev сервера
webServer: process.env.CI
  ? {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: false,
      timeout: 120000,
    }
  : undefined,
```

#### ✅ Исправление 6: Увеличены timeouts
**Файл:** `frontend/playwright.config.ts:47, 51`

```typescript
// Таймауты
actionTimeout: 15000,
navigationTimeout: 60000,  // было 30000

// Общий таймаут теста
timeout: 90000,  // было 60000
```

---

## 🔴 ПРОБЛЕМА 1: Медленная компиляция checkout страницы

**Количество падающих тестов:** 6
**Файл:** `frontend/tests/e2e/checkout.spec.ts`

### Симптомы
```
TimeoutError: page.goto: Timeout 60000ms exceeded.
Call log:
  - navigating to "http://localhost:3000/checkout", waiting until "load"
```

### Логи Docker
```
GET /checkout 200 in 35002ms
GET /checkout 200 in 36601ms
GET /checkout 200 in 33656ms
```

Страницы `/checkout` и `/checkout/success/123` грузятся **24-39 секунд**, что превышает текущий timeout в 60 секунд.

### Падающие тесты (строки)
1. ❌ `complete checkout flow from cart to success` - строка 203
2. ❌ `navigates to checkout page` - строка 237
3. ❌ `fills contact information correctly` - строка 250
4. ❌ `fills delivery address correctly` - строка 269
5. ❌ `selects delivery method` - строка 287
6. ❌ `displays success page with order number` - строка 310

### Решения (выбрать одно или несколько)

#### Вариант А: Увеличить timeout (быстрое решение)
**Файл:** `frontend/playwright.config.ts`

```typescript
// Увеличить navigationTimeout до 90-120 секунд
navigationTimeout: 120000,  // было 60000

// Увеличить общий timeout теста
timeout: 150000,  // было 90000
```

**Плюсы:** Быстро, работает сразу
**Минусы:** Тесты будут долго выполняться

#### Вариант Б: Оптимизировать компиляцию Next.js в Docker
**Файл:** `docker/docker-compose.yml` или `frontend/next.config.js`

Добавить webpack cache:
```javascript
// frontend/next.config.js
module.exports = {
  webpack: (config) => {
    config.cache = {
      type: 'filesystem',
      cacheDirectory: '.next/cache/webpack',
    };
    return config;
  },
};
```

#### Вариант В: Прогреть страницы перед тестами
Добавить в `beforeAll`:
```typescript
test.beforeAll(async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  // Прогреваем страницы
  await page.goto('/checkout', { waitUntil: 'networkidle' });
  await page.goto('/profile', { waitUntil: 'networkidle' });
  await context.close();
});
```

---

## 🔴 ПРОБЛЕМА 2: Strict mode violations для сообщений об ошибках

**Количество падающих тестов:** 3
**Файл:** `frontend/tests/e2e/checkout.spec.ts`

### Симптомы
```
Error: strict mode violation: locator('text=Некорректный формат email') resolved to 2 elements:
1) <p id="input-email-description" class="mt-1 text-[var(--color-accent-danger)]">Некорректный формат email</p>
2) <p class="sr-only" id="email-error">Некорректный формат email</p>
```

### Падающие тесты (строки)
1. ❌ `validates email format` - строка 359
2. ❌ `validates phone format` - строка 380
3. ❌ `validates postal code format` - строка 401

### Текущий код (некорректный)

**Строка 359-367:**
```typescript
test('validates email format', async ({ page }) => {
  await page.goto('/checkout');

  // Вводим некорректный email
  await page.fill('input[name="email"]', 'invalid-email');
  await page.fill('input[name="phone"]', testCheckoutData.phone); // blur

  // Проверяем ошибку формата email
  await expect(page.locator('text=Некорректный формат email')).toBeVisible();
  //                                                           ^^^^^^^^^^^
  //                                                           ПРОБЛЕМА: находит 2 элемента
```

**Строка 380-388:**
```typescript
test('validates phone format', async ({ page }) => {
  await page.goto('/checkout');

  // Вводим некорректный телефон
  await page.fill('input[name="phone"]', '123456');
  await page.fill('input[name="email"]', testCheckoutData.email); // blur

  // Проверяем ошибку формата
  await expect(page.locator('text=Формат: +7XXXXXXXXXX')).toBeVisible();
  //                                                       ^^^^^^^^^^^
  //                                                       ПРОБЛЕМА: находит 2 элемента
```

**Строка 401-409:**
```typescript
test('validates postal code format', async ({ page }) => {
  await page.goto('/checkout');

  // Вводим некорректный индекс
  await page.fill('input[name="postalCode"]', '123');
  await page.fill('input[name="email"]', testCheckoutData.email); // blur

  // Проверяем ошибку
  await expect(page.locator('text=6 цифр')).toBeVisible();
  //                                        ^^^^^^^^^^^
  //                                        ПРОБЛЕМА: находит 2 элемента
```

### РЕШЕНИЕ: Использовать .first() или ID селекторы

```typescript
// Вариант 1: Добавить .first()
await expect(page.locator('text=Некорректный формат email').first()).toBeVisible();

// Вариант 2: Использовать ID (предпочтительнее)
await expect(page.locator('#input-email-description')).toBeVisible();
await expect(page.locator('[id="input-телефон-description"]')).toBeVisible();
await expect(page.locator('[id="input-почтовый-индекс-description"]')).toBeVisible();

// Вариант 3: Использовать :not(.sr-only)
await expect(page.locator('text=Некорректный формат email').and(page.locator(':not(.sr-only)'))).toBeVisible();
```

---

## 🔴 ПРОБЛЕМА 3: Кнопка "Оформить заказ" не найдена

**Количество падающих тестов:** 4
**Файл:** `frontend/tests/e2e/checkout.spec.ts`

### Симптомы
```
TimeoutError: page.click: Timeout 15000ms exceeded.
Call log:
  - waiting for locator('button[type="submit"]:has-text("Оформить заказ")')
```

### Падающие тесты (строки)
1. ❌ `shows validation errors for empty required fields` - строка 336
2. ❌ `requires delivery method selection` - строка 446
3. ❌ `shows error message when order creation fails` - строка 549
4. ❌ `shows validation error from server` - строка 586
5. ❌ `handles network error gracefully` - строка 623

### Текущий код (проблемный)

**Строка 343:**
```typescript
// Пытаемся отправить пустую форму (клик по кнопке submit)
await page.click('button[type="submit"]:has-text("Оформить заказ")');
```

### Возможные причины
1. **Кнопка имеет другой текст** - возможно "Оформить" без слова "заказ"
2. **Кнопка disabled до загрузки** - нужно ждать enabled состояния
3. **Кнопка скрыта за другим элементом**
4. **Страница не загрузилась** - timeout на page.goto

### РЕШЕНИЕ: Исследовать и исправить

#### Шаг 1: Проверить реальный HTML кнопки
Открыть страницу `/checkout` в браузере и найти кнопку submit:

```bash
# Запустить тест с --headed для визуальной проверки
cd frontend && npx playwright test "shows validation errors" --headed --debug
```

#### Шаг 2: Использовать альтернативные селекторы

```typescript
// Вариант 1: Поиск по роли
await page.click('button[type="submit"]');

// Вариант 2: Поиск по тексту без :has-text
await page.getByRole('button', { name: /оформить/i }).click();

// Вариант 3: Ждать enabled состояния
await page.waitForSelector('button[type="submit"]:not([disabled])');
await page.click('button[type="submit"]');
```

#### Шаг 3: Добавить явное ожидание загрузки
```typescript
// Перед кликом:
await expect(page.locator('h2:has-text("Контактные данные")')).toBeVisible();
await page.waitForLoadState('networkidle');
```

---

## 🔴 ПРОБЛЕМА 4: SearchHistory не появляется при фокусе

**Количество падающих тестов:** 7
**Файл:** `frontend/tests/e2e/search-history.spec.ts`

### Симптомы
```
Error: element(s) not found
Locator: locator('[data-testid="search-history"]')
Expected: visible
Timeout: 5000ms
```

### Падающие тесты (строки)
1. ❌ `shows search history on focus with empty field` - строка 177
2. ❌ `hides history when typing` - строка 199
3. ❌ `clicking history item performs search` - строка 220
4. ❌ `removes individual history item` - строка 244
5. ❌ `clears all search history` - строка 271
6. ❌ `has correct ARIA attributes` - строка 362
7. ❌ `buttons have aria-labels` - строка 383
8. ❌ `Escape key closes history dropdown` - строка 404

### Логика отображения SearchHistory

**Файл:** `frontend/src/components/business/SearchAutocomplete/SearchAutocomplete.tsx:240-247`

```typescript
{/* История поиска - показывается при фокусе на пустом поле */}
{isFocused && query.trim().length === 0 && history.length > 0 && (
  <SearchHistory
    history={history}
    onSelect={handleHistorySelect}
    onRemove={removeSearch}
    onClear={clearHistory}
  />
)}
```

**Условия для отображения:**
1. ✅ `isFocused === true` - поле в фокусе
2. ✅ `query.trim().length === 0` - поле пустое
3. ❓ `history.length > 0` - **ПРОБЛЕМА: история пуста?**

### Проверка: Откуда берётся history?

**Файл:** `frontend/src/components/business/SearchAutocomplete/SearchAutocomplete.tsx:79`

```typescript
const { history, addSearch, removeSearch, clearHistory } = useSearchHistory();
```

**Хук:** `frontend/src/hooks/useSearchHistory.ts`

История хранится в localStorage с ключом `'search_history'`.

### Проблема в тестах

**Файл:** `frontend/tests/e2e/search-history.spec.ts:92-100`

```typescript
async function initSearchHistory(page: Page, queries: string[]) {
  await page.addInitScript(
    ({ key, data }) => {
      localStorage.setItem(key, JSON.stringify(data));
    },
    { key: STORAGE_KEY, data: queries }
  );
}
```

**STORAGE_KEY определён на строке 18:**
```typescript
const STORAGE_KEY = 'search_history';
```

### Возможные причины

1. **localStorage не устанавливается до page.goto**
   - `addInitScript` выполняется при создании нового документа
   - Нужно вызывать `initSearchHistory` **ДО** `page.goto`

2. **useSearchHistory не читает из localStorage**
   - Возможно хук не инициализируется при первом рендере

3. **SearchAutocomplete не используется на /catalog**
   - Нужно проверить `frontend/src/app/catalog/page.tsx`

### РЕШЕНИЕ: Пошаговая диагностика

#### Шаг 1: Проверить порядок вызовов

**Текущий код (строка 177-189):**
```typescript
test('shows search history on focus with empty field', async ({ page }) => {
  // Инициализируем историю
  await initSearchHistory(page, testSearchQueries.slice(0, 3));

  await page.goto('/catalog');  // ✅ Правильный порядок

  const searchField = page.locator('[data-testid="search-field"]').first();
  await expect(searchField).toBeVisible();

  await searchField.focus();

  // Ждём появления истории
  await expect(page.locator('[data-testid="search-history"]')).toBeVisible({ timeout: 5000 });
```

Порядок правильный. Проблема в другом.

#### Шаг 2: Проверить что история записалась в localStorage

Добавить после `initSearchHistory`:

```typescript
await initSearchHistory(page, testSearchQueries.slice(0, 3));
await page.goto('/catalog');

// ДИАГНОСТИКА: Проверить localStorage
const storageHistory = await page.evaluate(() => {
  const stored = localStorage.getItem('search_history');
  console.log('localStorage:', stored);
  return stored ? JSON.parse(stored) : [];
});
console.log('История из localStorage:', storageHistory);
```

#### Шаг 3: Проверить состояние компонента

```typescript
await searchField.focus();

// ДИАГНОСТИКА: Проверить состояние SearchAutocomplete
const debugInfo = await page.evaluate(() => {
  const searchAutocomplete = document.querySelector('[data-testid="search-autocomplete"]');
  return {
    exists: !!searchAutocomplete,
    html: searchAutocomplete?.outerHTML.substring(0, 200)
  };
});
console.log('SearchAutocomplete:', debugInfo);
```

#### Шаг 4: Проверить используется ли SearchAutocomplete

**Файл для проверки:** `frontend/src/app/catalog/page.tsx`

```bash
# Поиск использования SearchAutocomplete
grep -r "SearchAutocomplete" frontend/src/app/catalog/
grep -r "search-field" frontend/src/app/catalog/
```

Если SearchAutocomplete не используется на странице `/catalog`, нужно:
1. Добавить компонент на страницу
2. ИЛИ изменить тесты для использования страницы где он есть (главная `/`)

#### Шаг 5: Проверить focus событие

```typescript
await searchField.focus();

// Ждём дольше - возможно задержка в обработчике
await page.waitForTimeout(500);

// Проверить что фокус установился
const isFocused = await searchField.evaluate(el => el === document.activeElement);
console.log('Поле в фокусе:', isFocused);
```

#### Шаг 6: Кликнуть вместо focus

```typescript
// Вместо:
await searchField.focus();

// Попробовать:
await searchField.click();
await page.waitForTimeout(300);
```

---

## 🔴 ПРОБЛЕМА 5: URL encoding кириллицы

**Количество падающих тестов:** 1
**Файл:** `frontend/tests/e2e/search-history.spec.ts:300`

### Симптомы
```
Expected pattern: /\/search\?q=тренажёр/
Received string: "http://localhost:3000/search?q=%D1%82%D1%80%D0%B5%D0%BD%D0%B0%D0%B6%D1%91%D1%80"
```

### Падающий тест (строка 300)

```typescript
test('persists history between sessions', async ({ page }) => {
  await page.goto('/catalog');

  const searchField = page.locator('[data-testid="search-field"]').first();
  await expect(searchField).toBeVisible();

  // Добавляем запрос в историю
  await searchField.fill('тренажёр');
  await page.waitForTimeout(400);
  await searchField.press('Enter');

  // Проверяем, что URL изменился
  await expect(page).toHaveURL(/\/search\?q=тренажёр/);  // ❌ ОШИБКА
```

### РЕШЕНИЕ: Учесть URL encoding

```typescript
// Вариант 1: Упростить regex (убрать проверку параметра)
await expect(page).toHaveURL(/\/search\?q=/);

// Вариант 2: Использовать закодированную строку
await expect(page).toHaveURL(/\/search\?q=%D1%82%D1%80%D0%B5%D0%BD%D0%B0%D0%B6%D1%91%D1%80/);

// Вариант 3: Проверить параметр отдельно (РЕКОМЕНДУЕТСЯ)
const url = new URL(page.url());
expect(url.pathname).toBe('/search');
expect(url.searchParams.get('q')).toBe('тренажёр');
```

**Применить на строке 312:**

```typescript
// БЫЛО:
await expect(page).toHaveURL(/\/search\?q=тренажёр/);

// СТАЛО:
const url = new URL(page.url());
expect(url.pathname).toBe('/search');
expect(url.searchParams.get('q')).toBe('тренажёр');
```

---

## 🔴 ПРОБЛЕМА 6: URL redirect с encoding

**Количество падающих тестов:** 1
**Файл:** `frontend/tests/e2e/profile/edit-profile.spec.ts:34`

### Симптомы
```
Expected pattern: /\/login\?next=\/profile/
Received string: "http://localhost:3000/login?next=%2Fprofile"
```

### Падающий тест (строка 34)

```typescript
test('redirects unauthenticated users to login page', async ({ page }) => {
  // ACT
  await page.goto('/profile');

  // ASSERT
  await expect(page).toHaveURL(/\/login\?next=\/profile/);  // ❌ ОШИБКА
});
```

### РЕШЕНИЕ: Использовать закодированный URL

```typescript
// БЫЛО:
await expect(page).toHaveURL(/\/login\?next=\/profile/);

// СТАЛО (Вариант 1):
await expect(page).toHaveURL(/\/login\?next=%2Fprofile/);

// ИЛИ (Вариант 2 - более гибкий):
await expect(page).toHaveURL(/\/login\?next=/);

// ИЛИ (Вариант 3 - точная проверка параметра):
const url = new URL(page.url());
expect(url.pathname).toBe('/login');
expect(url.searchParams.get('next')).toBe('/profile');
```

---

## 🔴 ПРОБЛЕМА 7: Скрытая навигация на desktop

**Количество падающих тестов:** 1
**Файл:** `frontend/tests/e2e/profile/edit-profile.spec.ts:295`

### Симптомы
```
locator('a[href="/profile"]').first()
Expected: visible
Received: hidden

11 × locator resolved to <a href="/profile" class="... border-b-2 ...">...</a>
     - unexpected value "hidden"
```

### Падающий тест (строка 295)

```typescript
test('displays sidebar navigation on desktop', async ({ page }) => {
  // ARRANGE - установка viewport для desktop
  await page.setViewportSize({ width: 1440, height: 900 });

  // ACT
  await page.goto('/profile');

  // ASSERT
  await expect(page.locator('text=Личный кабинет')).toBeVisible();
  await expect(page.locator('a[href="/profile"]').first()).toBeVisible();  // ❌ ОШИБКА
```

### Причина
Первый найденный элемент `a[href="/profile"]` - это **мобильная табовая навигация**, которая скрыта на desktop через CSS `hidden md:flex`.

### РЕШЕНИЕ: Использовать sidebar-специфичный селектор

```typescript
// ВАРИАНТ 1: Искать только видимые элементы
await expect(page.locator('a[href="/profile"]:visible').first()).toBeVisible();

// ВАРИАНТ 2: Использовать селектор для sidebar (РЕКОМЕНДУЕТСЯ)
// Нужно проверить реальную структуру HTML sidebar
await expect(page.locator('aside a[href="/profile"]')).toBeVisible();
// ИЛИ
await expect(page.locator('nav.sidebar a[href="/profile"]')).toBeVisible();
// ИЛИ по data-testid
await expect(page.locator('[data-testid="profile-sidebar"] a[href="/profile"]')).toBeVisible();

// ВАРИАНТ 3: Фильтр по классам (если известны)
await expect(page.locator('a[href="/profile"].desktop-nav')).toBeVisible();
```

### Шаги для исправления

1. **Открыть страницу /profile в браузере** с viewport 1440x900
2. **Инспектировать sidebar** и найти селектор родительского элемента
3. **Обновить тест** с правильным селектором

Пример:
```typescript
// Если sidebar имеет класс или data-testid
await expect(page.locator('[data-testid="sidebar-nav"] a[href="/profile"]')).toBeVisible();
```

---

## 🔴 ПРОБЛЕМА 8: Сброс соединения Docker (единичный случай)

**Количество падающих тестов:** 1
**Файл:** `frontend/tests/e2e/search-history.spec.ts:329`

### Симптомы
```
Error: page.goto: net::ERR_CONNECTION_RESET at http://localhost:3000/catalog
```

### Падающий тест (строка 329)

```typescript
test('moves duplicate queries to top of history', async ({ page }) => {
  await initSearchHistory(page, ['мяч', 'кроссовки', 'футболка']);

  await page.goto('/catalog');  // ❌ ERR_CONNECTION_RESET
```

### Причина
Единичный сбой Docker контейнера или перезагрузка Next.js dev сервера.

### РЕШЕНИЕ

#### Вариант 1: Добавить retry для этого теста
```typescript
test('moves duplicate queries to top of history', async ({ page }) => {
  await initSearchHistory(page, ['мяч', 'кроссовки', 'футболка']);

  // Retry logic для page.goto
  let retries = 3;
  while (retries > 0) {
    try {
      await page.goto('/catalog', { timeout: 30000 });
      break;
    } catch (error) {
      retries--;
      if (retries === 0) throw error;
      await page.waitForTimeout(1000);
    }
  }
```

#### Вариант 2: Настроить глобальный retry в playwright.config.ts
Уже настроено:
```typescript
retries: process.env.CI ? 2 : 0,
```

Для локальной разработки включить:
```typescript
retries: 1,  // Retry failed tests once
```

#### Вариант 3: Увеличить timeout для page.goto
```typescript
await page.goto('/catalog', { timeout: 60000 });
```

---

## 📁 Ключевые файлы для работы

### Тестовые файлы (требуют исправления)
1. `frontend/tests/e2e/checkout.spec.ts` - 14 падающих тестов
2. `frontend/tests/e2e/search-history.spec.ts` - 10 падающих тестов
3. `frontend/tests/e2e/profile/edit-profile.spec.ts` - 2 падающих теста

### Компоненты для проверки
1. `frontend/src/components/business/SearchAutocomplete/SearchAutocomplete.tsx`
2. `frontend/src/components/business/SearchHistory/SearchHistory.tsx`
3. `frontend/src/components/ui/SearchField/SearchField.tsx`
4. `frontend/src/hooks/useSearchHistory.ts`

### Страницы для проверки
1. `frontend/src/app/checkout/page.tsx`
2. `frontend/src/app/catalog/page.tsx`
3. `frontend/src/app/profile/page.tsx`

### Конфигурация
1. `frontend/playwright.config.ts`

---

## 🚀 Команды для работы

### Проверка окружения
```bash
# Проверить что Docker контейнер запущен
docker ps | findstr frontend

# Проверить доступность frontend
curl http://localhost:3000

# Проверить логи Docker
docker logs freesport-frontend --tail=50
```

### Запуск тестов

```bash
# Запустить ВСЕ E2E тесты
cd frontend && npm run test:e2e

# Запустить конкретный файл тестов
cd frontend && npx playwright test checkout.spec.ts
cd frontend && npx playwright test search-history.spec.ts
cd frontend && npx playwright test edit-profile.spec.ts

# Запустить один конкретный тест
cd frontend && npx playwright test -g "validates email format"
cd frontend && npx playwright test -g "shows search history on focus"

# Запустить с визуальным интерфейсом (headed mode)
cd frontend && npx playwright test --headed

# Запустить с отладкой (пошагово)
cd frontend && npx playwright test --debug

# Посмотреть HTML отчёт
cd frontend && npm run test:e2e:report
```

### Отладка конкретных проблем

```bash
# Проблема 1-3: Checkout тесты
cd frontend && npx playwright test checkout.spec.ts --headed

# Проблема 4: SearchHistory
cd frontend && npx playwright test search-history.spec.ts --headed --debug

# Проблема 5-7: Profile тесты
cd frontend && npx playwright test edit-profile.spec.ts
```

---

## 🎯 План исправлений (рекомендуемый порядок)

### Этап 1: Быстрые победы (5-10 минут)
1. ✅ Проблема 2: Strict mode violations - добавить `.first()` (3 теста)
2. ✅ Проблема 5: URL encoding - изменить regex (1 тест)
3. ✅ Проблема 6: Redirect URL encoding - изменить regex (1 тест)

**Ожидаемый результат:** +5 тестов, итого 18/39 (46%)

### Этап 2: Средняя сложность (15-30 минут)
4. ✅ Проблема 7: Desktop navigation - найти правильный селектор (1 тест)
5. ✅ Проблема 3: Кнопка "Оформить заказ" - исследовать и исправить (4 теста)
6. ✅ Проблема 1: Увеличить timeout до 120 секунд (6 тестов)

**Ожидаемый результат:** +11 тестов, итого 29/39 (74%)

### Этап 3: Сложная диагностика (30-60 минут)
7. ✅ Проблема 4: SearchHistory - диагностика почему не появляется (7-8 тестов)

**Ожидаемый результат:** +7-8 тестов, итого 36-37/39 (92-95%)

### Этап 4: Опциональная оптимизация
8. 🔄 Проблема 8: Docker retry - настроить retry (игнорировать если не повторяется)
9. 🔄 Оптимизация: Webpack cache для ускорения компиляции

**Целевой результат:** 35-39/39 тестов (90-100%) ✅

---

## 📊 Таблица прогресса

| Проблема | Тестов | Сложность | Приоритет | Статус |
|----------|--------|-----------|-----------|--------|
| #2 Strict mode violations | 3 | 🟢 Легко | 🔥 Высокий | ⏳ Ожидает |
| #5 URL encoding кириллицы | 1 | 🟢 Легко | 🔥 Высокий | ⏳ Ожидает |
| #6 Redirect URL encoding | 1 | 🟢 Легко | 🔥 Высокий | ⏳ Ожидает |
| #7 Desktop navigation | 1 | 🟡 Средне | 🔥 Высокий | ⏳ Ожидает |
| #3 Кнопка "Оформить заказ" | 4 | 🟡 Средне | 🔥 Высокий | ⏳ Ожидает |
| #1 Медленная компиляция | 6 | 🟡 Средне | 🔶 Средний | ⏳ Ожидает |
| #4 SearchHistory не появляется | 7-8 | 🔴 Сложно | 🔥 Высокий | ⏳ Ожидает |
| #8 Docker connection reset | 1 | 🟢 Легко | 🔵 Низкий | ⏳ Ожидает |

**Легенда:**
- 🟢 Легко (< 10 мин)
- 🟡 Средне (10-30 мин)
- 🔴 Сложно (> 30 мин)
- 🔥 Высокий приоритет
- 🔶 Средний приоритет
- 🔵 Низкий приоритет

---

## ✅ Критерии успеха

1. ✅ **Минимум 35 из 39 тестов проходят** (90%)
2. ✅ Все критичные user flows работают:
   - Checkout flow (6 тестов)
   - Profile navigation (2 теста)
   - Search history (8 тестов)
3. ✅ Не должно быть timeout ошибок на основных страницах
4. ✅ Все strict mode violations исправлены

---

## 📝 Заметки для следующей сессии

### Важные детали окружения
- Frontend в Docker компилируется медленно (24-39 секунд для /checkout)
- Используется кириллица в URL параметрах → нужен URL encoding
- Некоторые компоненты дублируют ошибки (видимая + sr-only) → нужен .first()
- SearchAutocomplete может не использоваться на всех страницах → проверить catalog/page.tsx

### Потенциальные подводные камни
1. `addInitScript` выполняется при создании документа - порядок важен
2. `searchField.focus()` может не вызывать onFocus - попробовать click()
3. Desktop/mobile навигация используют один HTML с разными CSS - первый элемент может быть hidden
4. Playwright не умеет ждать Next.js компиляцию - нужны большие timeouts

### Полезные ресурсы
- [Playwright selectors](https://playwright.dev/docs/selectors)
- [Playwright debugging](https://playwright.dev/docs/debug)
- [React Testing Library best practices](https://testing-library.com/docs/queries/about/)

---

**Конец документа**
Версия: 1.0
Обновлено: 2026-01-10
