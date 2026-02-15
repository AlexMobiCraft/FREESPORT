# Story 32.4: Секция маркетинговых баннеров (UI)

Status: in-progress

## История

Как Пользователь,
Я хочу видеть карусель маркетинговых предложений под блоком "Быстрые ссылки",
Чтобы узнавать о текущих акциях, и они не мешали основному Hero-баннеру.

## Критерии приемки

1.  **Размещение и видимость**:
    - **Дано**: структура главной страницы,
    - **Когда**: страница рендерится,
    - **Тогда**: новая секция `MarketingBannersSection` отображается сразу под секцией "Быстрые ссылки" (FR8).

2.  **Обработка пустого состояния**:
    - **Дано**: секция маркетинговых баннеров,
    - **Когда**: API не возвращает активных маркетинговых баннеров,
    - **Тогда**: секция явно скрыта (ничего не рендерит) (FR10).

3.  **Производительность и UX (Загрузка)**:
    - **Дано**: секция отображается,
    - **Когда**: изображение загружается,
    - **Тогда**: Skeleton-лоадер или контейнер с фиксированным соотношением сторон предотвращает сдвиг макета (CLS) (NFR5).
    - **И**: изображение рендерится через `Next/Image` с корректными `sizes` и поддержкой форматов WebP/AVIF, без регрессии UX в текущей конфигурации `images.unoptimized` (NFR4).

4.  **Обработка ошибок (Изображение)**:
    - **Дано**: изображение баннера не загрузилось (404/Error),
    - **Когда**: происходит ошибка,
    - **Тогда**: этот конкретный слайд скрывается или заменяется плейсхолдером (NFR8).

5.  **Обработка ошибок (Компонент)**:
    - **Дано**: критическая ошибка рендера в компоненте,
    - **Когда**: компонент падает,
    - **Тогда**: Error Boundary перехватывает ошибку и скрывает секцию вместо падения всей страницы (NFR6).

6.  **Навигация**:
    - **Дано**: маркетинговый баннер,
    - **Когда**: кликнули по баннеру,
    - **Тогда**: пользователь перенаправляется по настроенному `cta_link`.

## Задачи / Подзадачи

- [x] **Настройка и каркас**
    - [x] Создать компонент `MarketingBannersSection` в `frontend/src/components/home/`.
    - [x] Экспортировать компонент из `frontend/src/components/home/index.ts`.
    - [x] Интегрировать компонент в `HomePage.tsx` сразу после `QuickLinksSection` и до `CategoriesSection`.

- [x] **Реализация**
    - [x] Получение баннеров через `bannersService.getActive('marketing')`.
    - [x] Интеграция хука `useBannerCarousel` для логики слайдера.
    - [x] Реализация рендеринга слайдов с использованием `Next/Image` (`sizes`, `loading`, `priority` по правилам секции).
    - [x] Реализация условного рендеринга (скрыть, если пусто).
    - [x] Добавить component-level `ErrorBoundary` для секции с fallback `null` (секция скрывается, HomePage продолжает работать).
    - [x] Навигация по клику реализуется через поле `cta_link` из API.

- [x] **UX и Стилизация**
    - [x] Реализовать состояние Skeleton-лоадера, соответствующее соотношению сторон.
    - [x] Обработка ошибок загрузки изображений (фоллбек или скрытие).
    - [x] Применить адаптивные стили (мобильные/десктоп).

- [x] **Тестирование**
    - [x] Создать юнит-тесты `MarketingBannersSection.test.tsx`.
    - [x] Настроить тестовые данные для marketing-баннеров: локально мокать `bannersService.getActive('marketing')` в тестах секции **или** переопределить MSW handler `/banners/` с учетом query `type=marketing`.
    - [x] Проверить состояние загрузки (скелетон).
    - [x] Проверить пустое состояние (null рендер).
    - [x] Проверить обработку ошибок API.
    - [x] Проверить обработку ошибки загрузки изображения (слайд скрывается или показывается placeholder согласно выбранной стратегии).
    - [x] Проверить, что `ErrorBoundary` перехватывает ошибку рендера и секция скрывается без падения страницы.
    - [x] Проверить навигацию по клику на баннер через `cta_link`.

### Финальный QA Checklist (Ready for Review)

- [x] **AC1 / FR8:** В `HomePage` секция рендерится сразу после `QuickLinksSection` и до `CategoriesSection`.
- [x] **AC2 / FR10:** При ответе API `[]` секция не рендерится (`null`).
- [x] **AC3 / NFR5:** Во время загрузки рендерится skeleton/контейнер с фиксированным aspect ratio (без layout shift в рамках компонента).
- [x] **AC3 / NFR4:** Слайды используют `Next/Image` с корректными `sizes`; форматы WebP/AVIF не деградируют UX при текущем `images.unoptimized`.
- [x] **AC4 / NFR8:** Ошибка загрузки изображения (onError) обрабатывается: слайд скрыт или заменен placeholder согласно принятой стратегии.
- [x] **AC5 / NFR6:** Component-level Error Boundary перехватывает render error; HomePage продолжает рендер остальных секций.
- [x] **AC6:** Клик по баннеру ведет на `cta_link` из API-контракта.
- [x] Проверены accessibility-атрибуты: `alt` у изображения, доступный label секции/элементов управления.
- [x] Проверено, что при API error компонент деградирует безопасно (без crash всей страницы).
- [x] Проверено, что при `banners.length > 1` работает навигация карусели (dots/controls), при `<=1` лишние контролы скрыты.

### Review Follow-ups (AI)

- [ ] **[HIGH][Security]** Валидировать `cta_link` на бэкенде (разрешить только внутренние пути или whitelist доменов) и добавить на фронтенде guard для предотвращения `javascript:` и внешних редиректов. [frontend/src/components/home/MarketingBannersSection.tsx:144-147, backend/apps/banners/models.py:71-74]
- [ ] **[HIGH][Reliability]** Добавить pre-check на пустой/битый `image_url` до рендера `Next/Image`, чтобы избежать падения компонента и гарантировать AC4 (скрытие только слайда, не всей секции). [frontend/src/components/home/MarketingBannersSection.tsx:149-157, backend/apps/banners/serializers.py:62-64]
- [ ] **[MEDIUM][AC1 Regression]** Создать интеграционный тест проверки порядка секций в HomePage (QuickLinks → MarketingBanners → Categories). [frontend/src/components/home/HomePage.tsx:46-53, story validation checklist:89-92]
- [ ] **[MEDIUM][UX Semantics]** Добавить `type="button"` к dots-кнопкам карусели для предотвращения неявного submit внутри форм. [frontend/src/components/home/MarketingBannersSection.tsx:173-182]
- [ ] **[LOW][Code Quality]** Убрать неиспользуемую переменную `fill` из mock Next.js Image в тестах. [frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx:48-69]

### Команды валидации (frontend)

- [x] `npm run lint`
- [x] `npm run test -- src/components/home/__tests__/MarketingBannersSection.test.tsx`
- [ ] `npm run test -- src/components/home/__tests__/HomePage.test.tsx` (если добавлен интеграционный тест порядка секций)
- [ ] `npm run test:coverage` (опционально перед merge)

## Заметки разработчика

### Архитектура
- **Компонент**: `MarketingBannersSection`
- **Сервис**: `bannersService` (уже существует, поддерживает тип 'marketing')
- **Хук**: `useBannerCarousel` (уже существует из Story 32.3)
- **Контракт API**: для перехода используется поле `cta_link` (не `target_url`).
- **Отказоустойчивость**: секция должна быть обернута в component-level Error Boundary с fallback `null`.
- **Тестовая инфраструктура**: глобальный MSW handler `/banners/` по умолчанию отдает hero-баннер; для этой story тесты должны явно формировать marketing-данные (через локальный mock сервиса или override handler на `type=marketing`).

### Ограничения
- **Изображения**: Обязательно использовать `Next/Image`; учитывать текущую конфигурацию `images.unoptimized` и не вводить противоречий с ней.
- **CLS**: Критично поддерживать контейнеры с фиксированным соотношением сторон до загрузки изображения.
- **Отказоустойчивость**: Главная страница никогда не должна ломаться, если эта маркетинговая секция упадет.

## Запись агента разработки

### Используемая модель агента
Claude Opus 4.6 (Claude Code CLI)

### Implementation Plan
- Создан `MarketingBannersSection` компонент с inline `MarketingBannerErrorBoundary` (class component, fallback: null)
- Внутренний `MarketingBannersCarousel` использует `bannersService.getActive('marketing')` + `useBannerCarousel` hook из Story 32.3
- Skeleton loader с `aspect-[21/9] md:aspect-[3/1]` для предотвращения CLS
- `Next/Image` с `sizes="(max-width: 768px) 100vw, 1280px"` и `loading="lazy"` (below the fold)
- Image error handling: `failedImages` Set + `onError` callback → слайд скрывается; если все изображения failed → секция null
- Dots navigation с `role="tab"` / `aria-selected` только при `visibleBanners.length > 1`
- Стратегия тестирования: direct mock `bannersService.getActive` через `vi.mock` (по аналогии с HeroSection)

### Completion Notes
- ✅ Все 20 unit-тестов проходят (AC1–AC6, accessibility, ErrorBoundary, image error, dots navigation)
- ✅ ESLint чист для `MarketingBannersSection.tsx`
- ✅ HeroSection.test.tsx (13 тестов) — без регрессий
- ✅ Все home component тесты (186/191 passed) — 5 падений в QuickLinksSection.test.tsx являются pre-existing (отсутствует MSW handler для `/categories-tree/`)
- Решение по image error: выбрана стратегия скрытия слайда (не placeholder), так как маркетинговый баннер без изображения не имеет смысла

### Decisions
- ErrorBoundary реализован inline в файле компонента (не как shared), так как в проекте нет существующего ErrorBoundary и story требует component-level boundary
- `loading="lazy"` вместо `priority` — секция ниже fold, lazy loading оптимален
- Не добавлен `unoptimized` prop на `Next/Image` — `next.config.ts` уже устанавливает `images.unoptimized: true` глобально

## File List

| File | Change |
|------|--------|
| `frontend/src/components/home/MarketingBannersSection.tsx` | Added |
| `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx` | Added |
| `frontend/src/components/home/index.ts` | Modified — added `MarketingBannersSection` export |
| `frontend/src/components/home/HomePage.tsx` | Modified — added `MarketingBannersSection` between QuickLinksSection and CategoriesSection |

## Change Log

| Date | Change |
|------|--------|
| 2026-02-15 | Story 32.4 implementation complete: MarketingBannersSection component with ErrorBoundary, skeleton, image error handling, carousel integration, 20 unit tests (Claude Opus 4.6) |
| 2026-02-15 | Code Review (AI): 5 follow-ups created (2 HIGH, 2 MEDIUM, 1 LOW). Status → in-progress. Issues: Security (cta_link validation), Reliability (image_url pre-check), AC1 regression (HomePage order test), UX semantics (button type), Code quality (unused var). |
