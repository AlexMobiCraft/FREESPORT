---
title: 'Маркетинговые баннеры'
slug: 'marketing-banners'
created: '2026-02-12'
status: 'review'
stepsCompleted: [1, 2, 3]
tech_stack: 
  - Django (Models, Migrations, DRF)
  - Next.js (React Components, Custom Hooks)
  - Tailwind CSS (Styling)
files_to_modify: 
  - backend/apps/banners/models.py
  - backend/apps/banners/views.py
  - backend/apps/banners/admin.py
  - frontend/src/services/bannersService.ts
  - frontend/src/types/banners.ts
  - frontend/src/hooks/useBannerCarousel.ts (New)
  - frontend/src/components/home/HeroSection.tsx
  - frontend/src/components/home/MarketingBannersSection.tsx (New)
  - frontend/src/components/home/HomePage.tsx
code_patterns: 
  - **Single Table Inheritance**: Использование одного поля `type` для разделения типов баннеров в БД.
  - **DRF Filtering**: Добавление параметра `type` в `ActiveBannersView` для фильтрации выборки.
  - **Custom Hook**: Выделение логики карусели в `useBannerCarousel` для переиспользования.
  - **Component Composition**: Создание нового компонента `MarketingBannersSection`.
test_patterns: 
  - **Backend**: Проверка фильтрации в API тестах (DRF APITestCase).
  - **Frontend**: Тестирование рендеринга и кастомного хука.
---

# Техническая спецификация: Маркетинговые баннеры

**Создано:** 2026-02-12

## Обзор

### Постановка проблемы

Отделу маркетинга необходим способ отображения блока сменяющихся маркетинговых баннеров под секцией "Быстрые ссылки" на главной странице, управляемых из админки. Также необходимо устранить дублирование логики каруселей на фронтенде.

### Решение

Мы расширим существующую сущность `Banner` и рефакторим фронтенд:
1.  **Backend**: Добавить поле `type` в модель `Banner` (`HERO` vs `MARKETING`).
2.  **API**: Обновить `ActiveBannersView` для фильтрации по типу. **Важно**: Строгая валидация типа.
3.  **Frontend**: Выделить общую логику карусели в хук `useBannerCarousel`.
4.  **Frontend**: Создать компонент `MarketingBannersSection`, использующий этот хук.

### Объем работ (Scope)

**Входит в объем:**
*   Backend: Миграция, админка, тесты модели.
*   API: Фильтрация по типу в `ActiveBannersView`.
*   Frontend: `useBannerCarousel` (refactor), `MarketingBannersSection`, обновление `HeroSection`.
*   Интеграция в `HomePage`.

**Не входит в объем:**
*   Сложная аналитика.
*   Изменения дизайна Hero баннеров (только рефакторинг логики).

## Контекст разработки

### Паттерны кодовой базы

*   `Banner` модель уже содержит всю необходимую логику.
*   `ActiveBannersView` использует `Banner.get_for_user`.
*   Frontend использует React Functional Components.

### Файлы для справки

| Файл | Назначение |
| ---- | ---------- |
| `backend/apps/banners/models.py` | Добавить `type` (CharField с choices). |
| `backend/apps/banners/views.py` | Добавить фильтрацию с валидацией. |
| `frontend/src/hooks/useBannerCarousel.ts` | Новый хук для логики автопрокрутки. |
| `frontend/src/components/home/HeroSection.tsx` | Рефакторинг на использование хука. |

### Технические решения

1.  **Типы баннеров**: `HERO = 'hero'`, `MARKETING = 'marketing'`.
2.  **API Validation**: Если передан невалидный `type`, возвращать `400 Bad Request` или пустой список (безопаснее пустой список, чтобы не ломать фронт при ошибках, но для отладки лучше знать). *Решение: Игнорировать некорректные типы и возвращать пустой список, чтобы не показывать не те баннеры.*

## План реализации

### Задачи

#### Backend

1.  [ ] **Добавить поддержку типов баннеров**
    *   **Файл**: `backend/apps/banners/models.py`
    *   **Действие**: Добавить `class BannerType(models.TextChoices)` (`HERO`, `MARKETING`).
    *   **Действие**: Добавить поле `type` (default=`HERO`).

2.  [ ] **Создать миграцию БД**
    *   **Действие**: `makemigrations`, `migrate`.

3.  [ ] **Обновить Admin Panel**
    *   **Файл**: `backend/apps/banners/admin.py`
    *   **Действие**: Добавить `type` в `list_display`, `list_filter`, `fieldsets`.

4.  [ ] **Реализовать фильтрацию в API**
    *   **Файл**: `backend/apps/banners/views.py`
    *   **Действие**: В `ActiveBannersView.list` получать `type`.
    *   **Действие**: Валидировать тип. Если валиден -> фильтровать. Если нет -> вернуть пустой список (или ошибку, если в debug). Если не передан -> default `hero`.

#### Frontend

5.  [ ] **Создать хук useBannerCarousel**
    *   **Файл**: `frontend/src/hooks/useBannerCarousel.ts`
    *   **Действие**: Перенести логику `useState(currentIndex)`, `useEffect` (interval), `setIsPaused` из `HeroSection`. Параметры: `itemsLength`, `intervalMs`. Возвращает: `currentIndex`, `setCurrentIndex`, `handlers` (onMouseEnter/Leave).

6.  [ ] **Обновить сервис и типы**
    *   **Файл**: `frontend/src/services/bannersService.ts`, `frontend/src/types/banners.ts`
    *   **Действие**: Добавить `type` в запрос `getActive`.

7.  [ ] **Рефакторинг HeroSection**
    *   **Файл**: `frontend/src/components/home/HeroSection.tsx`
    *   **Действие**: Использовать `useBannerCarousel`.
    *   **Действие**: Запрашивать `type='hero'`.

8.  [ ] **Создать MarketingBannersSection**
    *   **Файл**: `frontend/src/components/home/MarketingBannersSection.tsx`
    *   **Действие**: Использовать `useBannerCarousel`.
    *   **Действие**: Запрашивать `type='marketing'`.
    *   **Действие**: Верстка секции (адаптивная, меньше чем Hero).

9.  [ ] **Интеграция на Главную**
    *   **Файл**: `frontend/src/components/home/HomePage.tsx`
    *   **Действие**: Вставить `<MarketingBannersSection />`.

### Критерии приемки

1.  [ ] **AC 1: Admin**
    *   Администратор может создавать баннеры разных типов.
2.  [ ] **AC 2: API**
    *   API корректно фильтрует баннеры по типу. Невалидный тип не возвращает ничего.
3.  [ ] **AC 3: Frontend Reuse**
    *   `HeroSection` и `MarketingBannersSection` используют общий хук карусели.
4.  [ ] **AC 4: UI**
    *   Маркетинговые баннеры отображаются под Quick Links и автоматически прокручиваются.

## Дополнительный контекст

### Стратегия тестирования

*   **Backend**: Тесты на фильтрацию и валидацию типов.
*   **Frontend**: Проверить работу хука (unit test?) и компонентов.
