# Epic 21: Страница «Блог» — Brownfield Enhancement

<!-- Powered by BMAD™ Core -->

## Epic Goal

Реализовать полноценную систему управления блогом с возможностью создания, редактирования и публикации статей через Django Admin, а также страницы `/blog` для отображения списка статей и детальных страниц `/blog/{slug}`.

---

## Existing System Context

### Текущая функциональность

- **Backend:**
  - Модель `News` в `backend/apps/common/models.py` — референс-реализация
  - Модель `Category` уже существует и может быть переиспользована
  - Паттерны: `NewsListView`, `NewsDetailView`, `NewsSerializer`
  - Django Admin настроен для News — можно использовать как шаблон

- **Frontend:**
  - Страница `/news` и `/news/[slug]` — референс-реализация
  - Навигация Header готова к добавлению ссылки `/blog`
  - Teaser-блок на главной странице уже существует
  - UI компоненты: `NewsCard`, `NewsList`, `Breadcrumb` можно адаптировать

### Technology Stack

- **Frontend:** Next.js 15.5.7, React 19.1.0, TypeScript 5.0+, Tailwind CSS 4.0
- **Backend:** Django 4.2 LTS, DRF 3.14+, PostgreSQL 15+
- **Testing:** Vitest 2.1.5, React Testing Library, Pytest

### Integration Points

1. **API (новый):** `GET /api/v1/blog/` — список опубликованных статей с пагинацией
2. **API (новый):** `GET /api/v1/blog/{slug}/` — детальная статья
3. **Header Navigation:** добавить ссылку `/blog`
4. **Django Admin:** интерфейс управления статьями блога

---

## Enhancement Details

### Что добавляется

1. **Backend:**
   - Модель `BlogPost` в `backend/apps/common/models.py`
     - `title` (CharField, max_length=200) — заголовок
     - `slug` (SlugField, unique) — URL-идентификатор
     - `subtitle` (CharField, optional) — подзаголовок
     - `excerpt` (TextField, optional) — краткое описание для превью
     - `content` (TextField) — полное содержание статьи
     - `image` (ImageField) — главное изображение
     - `author` (CharField) — имя автора
     - `category` (ForeignKey → Category, optional) — категория
     - `is_published` (BooleanField) — флаг публикации
     - `published_at` (DateTimeField) — дата публикации
     - `meta_title` (CharField, optional) — SEO title
     - `meta_description` (TextField, optional) — SEO description
     - `created_at`, `updated_at` — аудит-поля
   - Сериализаторы: `BlogPostListSerializer`, `BlogPostDetailSerializer`
   - Views: `BlogPostListView`, `BlogPostDetailView`
   - URLs: `/api/v1/blog/`, `/api/v1/blog/{slug}/`
   - Django Admin: `BlogPostAdmin` с fieldsets и prepopulated_fields

2. **Frontend:**
   - Страница `/blog` — список статей с пагинацией
   - Страница `/blog/[slug]` — детальная страница статьи
   - Сервис `blogService.ts` — работа с API
   - Компоненты `BlogCard`, `BlogList` (адаптация NewsCard/NewsList)
   - SEO metadata для страниц
   - Добавление ссылки "Блог" в навигацию Header

### Integration Approach

- Модель `BlogPost` создаётся по образцу `News` для консистентности
- Переиспользование модели `Category` для классификации статей
- Frontend компоненты базируются на существующих News-компонентах
- SEO-оптимизация по паттерну страниц новостей

### Success Criteria

- [ ] Модель `BlogPost` создана и миграции применены
- [ ] Django Admin позволяет создавать/редактировать/публиковать статьи
- [ ] API endpoints возвращают список и детальные статьи
- [ ] Страница `/blog` отображает список опубликованных статей
- [ ] Страница `/blog/{slug}` отображает детальную статью
- [ ] SEO метаданные корректно настроены
- [ ] Responsive дизайн (mobile, tablet, desktop)
- [ ] Unit-тесты покрывают ≥70% кода

---

## Stories

### Story 21.1: Backend модель BlogPost и Django Admin

**Цель:** Создать модель `BlogPost` с полным набором полей и настроить Django Admin интерфейс.

**Задачи:**

- Добавить модель `BlogPost` в `backend/apps/common/models.py`
- Создать миграцию и применить её
- Настроить `BlogPostAdmin` в `backend/apps/common/admin.py`
- Написать unit-тесты для модели

**Поля модели:**
| Поле | Тип | Описание |
|------|-----|----------|
| title | CharField(200) | Заголовок статьи |
| slug | SlugField(200, unique) | URL-идентификатор |
| subtitle | CharField(200, blank) | Подзаголовок |
| excerpt | TextField(blank) | Краткое описание |
| content | TextField | Полное содержание |
| image | ImageField | Главное изображение |
| author | CharField(100, blank) | Имя автора |
| category | ForeignKey(Category) | Категория (nullable) |
| is_published | BooleanField | Флаг публикации |
| published_at | DateTimeField | Дата публикации |
| meta_title | CharField(200, blank) | SEO title |
| meta_description | TextField(blank) | SEO description |
| created_at | DateTimeField | Дата создания |
| updated_at | DateTimeField | Дата обновления |

**Estimated effort:** 0.5 дня

---

### Story 21.2: Backend API endpoints для блога

**Цель:** Создать REST API для получения списка и детальной информации о статьях блога.

**Задачи:**

- Создать `BlogPostListSerializer` и `BlogPostDetailSerializer`
- Создать `BlogPostListView` (GET /api/v1/blog/) с пагинацией
- Создать `BlogPostDetailView` (GET /api/v1/blog/{slug}/)
- Добавить маршруты в `urls.py`
- Написать интеграционные тесты для API

**Estimated effort:** 0.5 дня

---

### Story 21.3: Frontend страницы блога

**Цель:** Реализовать страницы `/blog` и `/blog/[slug]` на фронтенде.

**Задачи:**

- Создать `frontend/src/app/blog/page.tsx` — список статей
- Создать `frontend/src/app/blog/[slug]/page.tsx` — детальная страница
- Создать `frontend/src/services/blogService.ts` — API сервис
- Создать/адаптировать компоненты `BlogCard`, `BlogList`
- SEO metadata для обеих страниц
- Добавить ссылку "Блог" в Header navigation
- Responsive дизайн
- Unit-тесты

**Estimated effort:** 1-1.5 дня

---

## Compatibility Requirements

- [x] Существующие APIs остаются без изменений
- [ ] Схема БД расширяется (новая таблица BlogPost)
- [x] UI изменения следуют существующим паттернам (News pages)
- [x] Влияние на производительность минимально

---

## Risk Mitigation

- **Primary Risk:** Дублирование кода с News — может усложнить поддержку
- **Mitigation:** Максимально переиспользовать существующие компоненты и паттерны; рассмотреть базовый класс/миксин для общей логики
- **Rollback Plan:** Откатить миграции и удалить frontend страницы

---

## Definition of Done

- [ ] All stories completed with acceptance criteria met
- [ ] Existing functionality verified through testing
- [ ] Integration points working correctly
- [ ] Documentation updated appropriately
- [ ] No regression in existing features

---

## Story Manager Handoff

> Пожалуйста, разработайте детальные user stories для этого brownfield эпика. Ключевые моменты:
>
> - Это улучшение существующей системы на **Next.js 15 + Django 4.2**
> - **Integration points:** `/api/v1/blog/`, Header navigation, Django Admin
> - **Existing patterns to follow:** Epic 20 (News pages), модель News как референс
> - **Critical compatibility requirements:** существующий API `/news/` не должен затрагиваться
> - Каждая story должна включать верификацию существующей функциональности
>
> Эпик должен сохранять целостность системы, обеспечивая полноценное управление блогом.

---

## Change Log

| Date       | Version | Description                      | Author       |
|------------|---------|----------------------------------|--------------|
| 2025-12-27 | 1.0     | Initial epic draft               | John (PM)    |
