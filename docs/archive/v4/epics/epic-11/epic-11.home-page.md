# Epic 11: Главная страница - Frontend Enhancement

**Создан:** 2025-11-16
**Статус:** Запланирован
**Приоритет:** P0 (критичный)
**Длительность:** 2 недели
**Зависимости:** Эпик 10 (Фундамент и подготовка), Эпик 2 (Backend API)

---

## Epic Goal

Реализовать главную страницу FREESPORT с динамическими блоками контента (баннеры, хиты продаж, новинки, категории, новости) и формой подписки на рассылку, обеспечив SEO-оптимизацию через SSR/SSG и ролевую персонализацию для B2B/B2C пользователей.

---

## Epic Description

### Existing System Context

**Текущая функциональность:**

- ✅ Backend API готов с эндпоинтами для продуктов, категорий, новостей (Эпик 2)
- ✅ Базовый UI Kit реализован в `src/components/ui/` (Эпик 10)
- ✅ Zustand stores настроены (`authStore`, `cartStore`)
- ✅ API клиент с интерцепторами для JWT аутентификации
- ✅ TypeScript типы сгенерированы из `api-spec.yaml`

**Технологический стек:**

- Next.js 14+ App Router с SSR/SSG
- TypeScript 5.0+
- Zustand (управление состоянием)
- Axios (API клиент)
- Tailwind CSS 4.0 + Design System tokens
- Jest + React Testing Library (тестирование)

**Точки интеграции:**

- Backend API эндпоинты:
  - `GET /api/products/hits` — хиты продаж
  - `GET /api/products/new` — новинки
  - `GET /api/categories` — список категорий для главной
  - `GET /api/news` — новостные блоки
  - `POST /api/subscribe` — подписка на рассылку
- Компоненты UI Kit из `src/components/ui/`:
  - `Header`, `Button`, `Card`, `Badge`, `Input`
- Zustand stores:
  - `authStore` для определения роли пользователя (B2B/B2C)

### Enhancement Details

**Что добавляется:**

1. **Hero-секция с ролевыми баннерами:**
   - Адаптивный баннер с CTA для B2B клиентов ("Узнать оптовые условия")
   - Баннер для B2C клиентов ("Новая коллекция 2025")
   - Переключение контента на основе роли пользователя из `authStore`

2. **Динамические блоки контента:**
   - Блок "Хиты продаж" (интеграция с `/api/products/hits`)
   - Блок "Новинки" (интеграция с `/api/products/new`)
   - Блок "Популярные категории" (интеграция с `/api/categories`)
   - Блок "Новости и акции" (интеграция с `/api/news`)

3. **Форма подписки на рассылку:**
   - Валидация email (React Hook Form)
   - Интеграция с `/api/subscribe`
   - Success/Error states

4. **Адаптивная вёрстка:**
   - Mobile-first подход
   - Breakpoints: mobile (< 768px), tablet (768-1024px), desktop (> 1024px)
   - Оптимизация изображений (Next.js Image)

**Как интегрируется:**

- Использует компоненты из UI Kit (Эпик 10)
- Получает данные через API сервисы (`productsService`, `categoriesService`, `newsService`)
- Рендерится с использованием Next.js SSG для SEO (ISR с revalidation: 3600)
- Применяет токены дизайн-системы из `frontend/docs/design-system.json`

**Критерии успеха:**

- ✅ Главная страница загружается за < 2 секунды (LCP)
- ✅ SEO метатеги корректно заполнены (title, description, OG tags)
- ✅ Ролевые баннеры корректно отображаются для B2B/B2C
- ✅ Все динамические блоки загружаются из API
- ✅ Форма подписки работает с валидацией
- ✅ Адаптивная вёрстка на всех устройствах
- ✅ Unit-тесты покрытие 80%+
- ✅ PageSpeed score > 70

---

## User Stories

### Story 11.1: Hero-секция и Layout главной страницы

**Описание:** Создать базовую структуру главной страницы с Hero-секцией, включающей ролевые баннеры для B2B/B2C пользователей.

**Acceptance Criteria:**

- Реализован роут `/` (src/app/page.tsx)
- Hero-секция с баннером адаптируется под роль пользователя (authStore)
- Применены токены дизайн-системы (colors.primary, spacing, typography)
- Адаптивная вёрстка (mobile/tablet/desktop)
- SSG с ISR (revalidate: 3600)
- SEO метатеги заполнены

**Референсные документы:**

- `docs/frontend-development-plan.md` (строки 44-45)
- `docs/front-end-spec.md` (строки 54-205)
- `frontend/docs/design-system.json` (components: Header, Badge)
- `docs/prd/user-interface-design-goals.md` (строки 23-31)

---

### Story 11.2: Динамические блоки контента (Хиты, Новинки, Категории)

**Описание:** Реализовать блоки "Хиты продаж", "Новинки" и "Популярные категории" с интеграцией с Backend API.

**Acceptance Criteria:**

- Блок "Хиты продаж" загружает данные из `GET /api/products/hits`
- Блок "Новинки" загружает данные из `GET /api/products/new`
- Блок "Популярные категории" загружает данные из `GET /api/categories`
- Использованы компоненты `Card`, `Badge` из UI Kit
- Реализована горизонтальная прокрутка для товарных блоков
- Loading states и Error states обработаны
- Unit-тесты с MSW моками для всех API вызовов

**Референсные документы:**

- `docs/api-spec.yaml` (endpoints: /products/hits, /products/new, /categories)
- `frontend/docs/design-system.json` (components: Card, Badge, RecommendationsRow)
- `frontend/docs/testing-standards.md` (MSW mocking)

---

### Story 11.3: Форма подписки на рассылку и блок новостей

**Описание:** Реализовать форму подписки на email-рассылку и блок "Новости и акции".

**Acceptance Criteria:**

- Форма подписки с валидацией email (React Hook Form)
- Интеграция с `POST /api/subscribe`
- Success toast при успешной подписке
- Error handling для сетевых ошибок
- Блок "Новости и акции" загружает данные из `GET /api/news`
- Карточки новостей с превью изображений (Next.js Image)
- Адаптивная вёрстка формы и блока новостей
- Unit-тесты для валидации формы
- Integration-тесты для API вызовов

**Референсные документы:**

- `docs/api-spec.yaml` (endpoints: /subscribe, /news)
- `frontend/docs/design-system.json` (components: Input, Button)
- `docs/front-end-spec.md` (UI patterns для форм)

---

## Compatibility Requirements

- [ ] Header компонент остаётся неизменным (используется из Эпика 10)
- [ ] authStore API не изменяется (совместимость с Эпиком 14)
- [ ] cartStore не затрагивается (используется в Эпике 15)
- [ ] API эндпоинты соответствуют api-spec.yaml без изменений
- [ ] Все компоненты UI Kit используются без модификаций
- [ ] Производительность: LCP < 2s, CLS < 0.1

---

## Risk Mitigation

**Основной риск:** API эндпоинты для новостей и подписки могут быть не готовы к моменту разработки.

**Митигация:**

- Использовать MSW моки для разработки и тестирования
- Параллельная коммуникация с Backend командой для уточнения контрактов API
- Создать fallback контент для блоков на случай ошибок API

**Риск 2:** Проблемы производительности из-за большого количества изображений товаров.

**Митигация:**

- Использовать Next.js Image с lazy loading
- Реализовать priority loading для hero-изображений
- Оптимизировать изображения в формате WebP
- Добавить skeleton loaders для улучшения perceived performance

**Rollback Plan:**

- Если критические баги в production, откатить deploy через CI/CD
- Использовать feature flags для отключения проблемных блоков
- Подготовить статичную версию главной страницы как fallback

---

## Definition of Done

- [ ] Все 3 user stories завершены с acceptance criteria выполнены
- [ ] Hero-секция с ролевыми баннерами работает корректно
- [ ] Все динамические блоки интегрированы с Backend API
- [ ] Форма подписки валидирует и отправляет данные
- [ ] Адаптивная вёрстка протестирована на mobile/tablet/desktop
- [ ] SEO метатеги заполнены (title, description, OG tags)
- [ ] SSG/ISR настроен с revalidation: 3600
- [ ] Unit-тесты покрытие 80%+ (Jest + RTL)
- [ ] Integration-тесты с MSW моками для всех API
- [ ] PageSpeed score > 70 (Lighthouse)
- [ ] ESLint/Prettier проверки пройдены
- [ ] TypeScript без ошибок и без `as any`
- [ ] Code review завершён
- [ ] Существующий функционал не сломан (regression tests)
- [ ] CI/CD pipeline зелёный
- [ ] Документация обновлена (README, JSDoc для компонентов)

---

## Technical Notes

### Файловая структура:

```
src/
├── app/
│   ├── page.tsx                    # Главная страница (/)
│   └── layout.tsx                  # Global layout (из Эпика 10)
├── components/
│   ├── ui/                         # UI Kit (из Эпика 10)
│   │   ├── Header.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Button.tsx
│   │   └── Input.tsx
│   └── home/                       # Компоненты главной страницы
│       ├── HeroSection.tsx
│       ├── HitsSection.tsx
│       ├── NewArrivalsSection.tsx
│       ├── CategoriesSection.tsx
│       ├── NewsSection.tsx
│       └── SubscribeForm.tsx
├── services/
│   ├── api-client.ts               # Axios клиент (из Эпика 10)
│   ├── productsService.ts
│   ├── categoriesService.ts
│   ├── newsService.ts
│   └── subscribeService.ts
├── stores/
│   ├── authStore.ts                # Zustand (из Эпика 10)
│   └── cartStore.ts
└── types/
    └── api.ts                      # Сгенерированные типы
```

### API интеграция:

```typescript
// Пример использования productsService
import { productsService } from '@/services/productsService';

export default async function HomePage() {
  const hits = await productsService.getHits({ limit: 8 });
  const newProducts = await productsService.getNew({ limit: 8 });

  return (
    <main>
      <HeroSection />
      <HitsSection products={hits} />
      <NewArrivalsSection products={newProducts} />
      ...
    </main>
  );
}
```

### Дизайн-токены:

```tsx
// Применение токенов из design-system.json
<div className="bg-neutral-100 text-text-primary">
  <h1 className="text-display-l font-bold">Главная страница FREESPORT</h1>
  <Button variant="primary">Перейти в каталог</Button>
</div>
```

---

## Dependencies

**Блокирующие зависимости:**

- ✅ Эпик 10: Фундамент и подготовка (UI Kit, stores, API client)
- ✅ Эпик 2: Backend API (products, categories, news endpoints)

**Разблокирует:**

- Эпик 12: Каталог товаров (использует компоненты карточек товаров)
- Эпик 13: Карточка товара (навигация из главной в детальную карточку)

---

## Референсные документы

1. **Frontend Development Plan:** `docs/frontend-development-plan.md` (раздел 3.1, строки 44-45)
2. **Front-End Spec:** `docs/front-end-spec.md` (раздел "Информационная архитектура", строки 54-205)
3. **PRD UI Design Goals:** `docs/prd/user-interface-design-goals.md` (раздел "Core Screens", строки 23-31)
4. **Design System:** `frontend/docs/design-system.json` (компоненты: Header, Card, Badge, Button, Input)
5. **API Spec:** `docs/api-spec.yaml` (эндпоинты: /products/hits, /products/new, /categories, /news, /subscribe)
6. **Testing Standards:** `frontend/docs/testing-standards.md` (MSW mocking, coverage requirements)

---

## Next Steps

1. ✅ Epic утверждён и готов к декомпозиции
2. 🔄 Создать детальные user stories с задачами (Story Manager)
3. 🔄 Настроить MSW моки для API эндпоинтов
4. 🔄 Начать разработку с Story 11.1 (Hero-секция)
5. 🔄 Провести code review после каждой story
6. 🔄 Запустить Lighthouse аудит после завершения эпика

---

**Контакты:**

- **Product Owner:** Sarah 📝
- **Story Manager:** Sam 📋
- **Developer:** Cascade 💻

---

**Статус:** ✅ Готов к разработке
**Последнее обновление:** 2025-11-16
**Автор:** Sarah (PO Agent)
