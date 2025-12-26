# Epic 20: Страница «Новости» — Brownfield Enhancement

<!-- Powered by BMAD™ Core -->

## Epic Goal

Реализовать полноценную страницу новостей `/news` с возможностью просмотра списка и детальных страниц новостей, а также добавить блок «Новости» на главную страницу для привлечения пользователей к актуальному контенту.

---

## Existing System Context

### Текущая функциональность

- **Backend API:**
  - Модель `News` уже реализована в `backend/apps/common/models.py`
  - Поля модели: title, slug, excerpt, content, image, author, category, is_published, published_at, created_at, updated_at
  - API endpoint `GET /api/v1/news/` — список опубликованных новостей с пагинацией
  - Сериализатор `NewsSerializer` с полной информацией о новости
  - Админка Django настроена для управления новостями

- **Frontend:**
  - Навигация в Header уже содержит ссылку `/news`
  - Страница `/news` ещё не реализована (404)
  - UI компоненты: `FeatureCard`, `Breadcrumb`, `Button` доступны из Story 19.1

### Technology Stack

- **Frontend:** Next.js 15.5.7, React 19.1.0, TypeScript 5.0+, Tailwind CSS 4.0
- **Backend:** Django 4.2 LTS, DRF 3.14+, PostgreSQL 15+
- **Testing:** Vitest 2.1.5, React Testing Library, Pytest

### Integration Points

1. **API:** `GET /api/v1/news/` — существующий endpoint для списка
2. **API (новый):** `GET /api/v1/news/{slug}/` — endpoint для детальной новости
3. **Header Navigation:** уже содержит ссылку `/news`
4. **Homepage:** требуется добавить блок «Новости»

---

## Enhancement Details

### Что добавляется/изменяется

1. **Backend:**
   - Добавить endpoint `GET /api/v1/news/{slug}/` для получения детальной новости
   - Добавить сериализатор `NewsDetailSerializer` (опционально)

2. **Frontend:**
   - Создать страницу `/news` со списком новостей
   - Создать страницу `/news/[slug]` для детальной новости
   - Добавить блок «Новости» на главную страницу (`/test`)
   - Добавить сервис `newsService.ts` для работы с API

### Integration Approach

- Использовать существующий паттерн Server Components для SEO
- Следовать design system проекта (Tailwind CSS, цветовая схема)
- Reuse компонентов из Story 19.1 (`Breadcrumb`, карточки)
- Пагинация по аналогии с каталогом товаров

### Success Criteria

- [ ] Страница `/news` отображает список опубликованных новостей
- [ ] Страница `/news/{slug}` отображает детальную новость
- [ ] Блок «Новости» на главной отображает 3-4 последние новости
- [ ] SEO метаданные корректно настроены
- [ ] Responsive дизайн (mobile, tablet, desktop)
- [ ] Unit-тесты покрывают ≥70% кода

---

## Stories

### Story 20.1: Backend API для детальной новости

**Цель:** Добавить endpoint для получения одной новости по slug.

**Задачи:**

- Создать `NewsDetailView` в `backend/apps/common/views.py`
- Добавить маршрут `path("news/<slug:slug>/", ...)` в `urls.py`
- Написать тесты для нового endpoint

**Estimated effort:** 0.5 дня

---

### Story 20.2: Frontend страницы новостей

**Цель:** Реализовать страницы `/news` и `/news/[slug]`.

**Задачи:**

- Создать `frontend/src/app/news/page.tsx` — список новостей
- Создать `frontend/src/app/news/[slug]/page.tsx` — детальная страница
- Создать `frontend/src/services/newsService.ts` — API сервис
- Добавить компоненты `NewsCard`, `NewsList`
- SEO metadata для обеих страниц
- Responsive дизайн
- Unit-тесты

**Estimated effort:** 1-1.5 дня

---

### Story 20.3: Блок «Новости» на главной странице

**Цель:** Добавить teaser-блок новостей на главную страницу.

**Задачи:**

- Создать компонент `NewsTeaser` (аналогично `AboutTeaser`)
- Интегрировать в главную страницу `/test`
- Responsive дизайн
- Unit-тесты

**Estimated effort:** 0.5 дня

---

## Compatibility Requirements

- [x] Существующие APIs остаются без изменений (`/api/v1/news/` сохраняется)
- [x] Схема БД не изменяется (модель `News` уже существует)
- [x] UI изменения следуют существующим паттернам
- [x] Влияние на производительность минимально

---

## Risk Mitigation

- **Primary Risk:** Отсутствие данных — если в БД нет новостей, страницы будут пустыми
- **Mitigation:** Добавить empty state UI; создать тестовые новости через админку
- **Rollback Plan:** При необходимости откатить — удалить frontend страницы, backend endpoint остаётся

---

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] Existing functionality verified through testing
- [x] Integration points working correctly
- [x] Documentation updated appropriately
- [x] No regression in existing features

---

## Story Manager Handoff

> Пожалуйста, разработайте детальные user stories для этого brownfield эпика. Ключевые моменты:
>
> - Это улучшение существующей системы на **Next.js 15 + Django 4.2**
> - **Integration points:** `/api/v1/news/`, Header navigation, Homepage
> - **Existing patterns to follow:** Story 19.3 (About page), компоненты из 19.1
> - **Critical compatibility requirements:** существующий API `/news/` не должен ломаться
> - Каждая story должна включать верификацию существующей функциональности
>
> Эпик должен сохранять целостность системы, обеспечивая отображение новостей на фронтенде.

---

## Change Log

| Date       | Version | Description                      | Author       |
|------------|---------|----------------------------------|--------------|
| 2025-12-26 | 1.0     | Initial epic draft               | John (PM)    |
