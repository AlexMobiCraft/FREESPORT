# Epic 14: Миграция на сине-голубую цветовую схему

> **Тип:** Brownfield Enhancement
> **Версия:** 1.0
> **Дата создания:** 2025-11-25
> **Приоритет:** High
> **Story Points:** 21
> **Длительность:** 5-7 рабочих дней

---

## Epic Goal

Обновить визуальную идентичность платформы FREESPORT с графитово-серой цветовой палитры на современную сине-голубую схему, повысив узнаваемость бренда, улучшив визуальную иерархию и конверсию CTA-элементов без изменения функциональности системы.

---

## Epic Description

### Existing System Context

**Текущая реализация:**

- Дизайн-система базируется на графитово-серой палитре (#1F1F1F основной)
- Токены определены в `docs/frontend/design-system.json` v2.0.0
- CSS-переменные реализованы через Tailwind CSS 4.0 в `frontend/src/app/globals.css`
- 25+ UI компонентов используют комбинацию токенов и хардкод цветов
- Epic 11, 12, 13 завершены с текущей цветовой схемой

**Технологический стек:**

- **Frontend:** Next.js 15.4.6, React 19.1.0, Tailwind CSS 4.0, TypeScript 5.0+
- **Design System:** Tokenized система с JSON спецификацией
- **Testing:** Vitest 2.1.5, React Testing Library 16.3.0, MSW 2.12.2

**Интеграционные точки:**

- design-system.json → источник истины для токенов
- globals.css → CSS-переменные Tailwind
- UI Components (Button, Badge, Checkbox, Toggle, Tabs, Toast, Input, Header, Pagination)
- Frontend Specification документация
- Story документы Epic 11, 12, 13

### Enhancement Details

**Что изменяется:**

**1. Цветовая палитра:**

- **Primary:** #1F1F1F (графитовый) → #0060FF (синий)
- **Secondary:** #3D3D3D (серый) → #00B7FF (голубой)
- **Accent Success:** #4D4D4D → #00AA5B (зелёный)
- **Accent Warning:** #6A6A6A → #F5A623 (оранжевый)
- **Accent Danger:** #2B2B2B → #E53935 (красный)
- **Accent Promo:** #8A8A8A → #FF2E93 (розовый)
- **Neutral шкала:** Обновление 7 из 9 оттенков с холодным сине-серым подтоном
- **Text цвета:** Обновление для улучшенной контрастности

**2. UI компоненты с хардкодом:**

- Button (primary, secondary, subtle variants)
- Badge (new, hit, promo, sale, discount variants)
- Checkbox (checked states)
- Toggle (track ON color)
- Pagination (active page)
- Header (cart badge)
- Tabs (active text)
- Toast (border colors)
- Input (focus states)

**3. Документация:**

- design-system.json → v2.1.0
- frontend/src/app/globals.css → обновление всех CSS-переменных
- docs/front-end-spec.md → обновление цветовых таблиц и примеров
- Story документы Epic 11 (11.0, 11.1, 11.2) → синхронизация цветовых AC

**Как интегрируется:**

- **Фаза 1:** Обновление источников истины (design-system.json, globals.css)
- **Фаза 2:** Рефакторинг UI компонентов (замена хардкод на токены)
- **Фаза 3:** Синхронизация документации
- **Фаза 4:** Тестирование (unit, visual regression, accessibility, manual)
- **Фаза 5:** Деплой через staging → production

**Success Criteria:**

**Технические:**

- ✅ Все unit тесты проходят (100%)
- ✅ Контрастность WCAG AA соблюдена (проверено в color-scheme-migration.md)
- ✅ Нет хардкод HEX кодов в компонентах (кроме badge bg специфических)
- ✅ design-system.json v2.1.0 синхронизирован с globals.css
- ✅ PageSpeed >70 сохранён на всех страницах
- ✅ Visual regression tests обновлены

**Бизнес:**

- ✅ Design Lead утвердил визуальную реализацию
- ✅ Product Owner одобрил изменения
- ✅ QA подписал acceptance testing
- ✅ Нет регрессии функциональности

---

## Stories

Эпик разбит на 5 логически последовательных stories для безопасного внедрения:

### Story 14.1: Обновление дизайн-системы и CSS токенов

**Цель:** Обновить источники истины для цветовых токенов
**Story Points:** 3
**Приоритет:** 🔴 Критический (блокирует остальные stories)

**Scope:**

- Обновить design-system.json до v2.1.0
- Обновить все CSS-переменные в globals.css
- Валидация JSON и CSS синтаксиса
- Проверка автоприменения токенов на dev сервере

**Deliverables:**

- design-system.json v2.1.0 с новой палитрой
- globals.css с обновлёнными CSS-переменными
- Git commit с детальным changelog

---

### Story 14.2: Рефакторинг UI Kit компонентов

**Цель:** Заменить хардкод цветов на токены в core UI компонентах
**Story Points:** 8
**Приоритет:** 🔴 Критический

**Scope:**

- Рефакторинг 9 компонентов: Button, Badge, Checkbox, Toggle, Tabs, Input, Toast, Link
- Замена всех хардкод HEX значений на Tailwind токены
- Обновление всех вариантов и состояний (hover, active, focus, disabled)
- Unit тесты для каждого компонента

**Deliverables:**

- 9 обновлённых компонентов с токенами
- Все unit тесты проходят
- Code review и approval
- Git commit с детальным описанием изменений

---

### Story 14.3: Обновление Page-level компонентов

**Цель:** Синхронизировать цвета в компонентах страниц
**Story Points:** 3
**Приоритет:** 🟠 Высокий

**Scope:**

- Обновление Pagination в catalog page
- Обновление Header (навигация, cart badge)
- Проверка SearchFilters, ProductGallery, ProductSummary (уже используют токены)
- Visual testing на ключевых страницах

**Deliverables:**

- Обновлённые page components
- Visual screenshots до/после
- Manual testing checklist завершён

---

### Story 14.4: Синхронизация документации

**Цель:** Обновить всю проектную документацию с новыми цветами
**Story Points:** 5
**Приоритет:** 🟡 Средний

**Scope:**

- Обновление docs/front-end-spec.md (цветовые таблицы, примеры)
- Синхронизация story документов Epic 11 (11.0, 11.1, 11.2)
- Обновление color-scheme-migration.md (статус → Реализовано)
- Добавление примечаний в завершённые Epic
- Обновление changelog в design-system.json

**Deliverables:**

- Обновлённая frontend спецификация
- Синхронизированные story docs (3 файла)
- Финальный migration report
- Git commit с документацией

---

### Story 14.5: Комплексное тестирование и деплой

**Цель:** Провести полное тестирование и развернуть изменения
**Story Points:** 2
**Приоритет:** 🔴 Критический

**Scope:**

- Автоматизированное тестирование (unit, snapshot update)
- Accessibility audit (WCAG AA контрастность)
- Visual regression testing на 3 breakpoints
- Manual testing на 4 браузерах (Chrome, Firefox, Safari, Edge)
- Cross-device testing (Desktop, Tablet, Mobile)
- Staging deployment + smoke tests
- Production deployment + monitoring

**Deliverables:**

- Все тесты проходят (100%)
- QA sign-off документ
- Staging approval от stakeholders
- Production deployment успешен
- Post-deploy monitoring report (24 часа)

---

## Compatibility Requirements

### Обратная совместимость

✅ **Сохраняется:**

- [ ] Все существующие API endpoints работают без изменений
- [ ] Database schema остаётся неизменной
- [ ] Функциональность UI компонентов идентична
- [ ] Props интерфейсы компонентов не меняются
- [ ] Старые Tailwind классы (`bg-gray-*`) продолжают работать

✅ **Автоматически обновляется:**

- [ ] Компоненты использующие CSS-переменные (`var(--color-primary)`)
- [ ] Tailwind utility классы (`bg-primary`, `text-primary`)
- [ ] Большинство компонентов без хардкода

⚠️ **Требует ручного обновления:**

- [ ] Компоненты с хардкод HEX значениями (8 файлов)
- [ ] Inline styles с цветами (если есть)
- [ ] Visual snapshot тесты

### Performance Impact

✅ **Минимальное влияние:**

- [ ] Bundle size не увеличивается (только значения токенов меняются)
- [ ] Runtime performance не затронута
- [ ] CSS компиляция Tailwind без замедления
- [ ] PageSpeed >70 сохранён

---

## Risk Mitigation

### Primary Risk: Пропущенный хардкод цветов в компонентах

**Вероятность:** Средняя
**Влияние:** Среднее (визуальные несоответствия)

**Митигация:**

1. Автоматический grep search по паттерну `#[0-9A-Fa-f]{6}` во всех `.tsx` файлах
2. Code review всех изменённых компонентов
3. Visual regression testing для обнаружения несоответствий
4. Manual QA checklist для всех UI состояний

**Rollback Plan:**

```bash
# Немедленный rollback (15 минут)
git revert <migration-commits>
git push origin main
# Deploy previous version через CI/CD
```

---

### Secondary Risk: Конфликт с будущими Epic

**Вероятность:** Низкая (Epic 11-13 завершены)
**Влияние:** Низкое

**Митигация:**

1. Все будущие Epic будут автоматически использовать новую палитру через токены
2. Документация содержит примеры использования новых цветов
3. Design System v2.1.0 — источник истины для разработки

---

### Tertiary Risk: Проблемы контрастности на edge cases

**Вероятность:** Очень низкая (проверено в migration doc)
**Влияние:** Высокое (accessibility нарушение)

**Митигация:**

1. Контрастность WCAG AA уже проверена в color-scheme-migration.md:
   - #0060FF на #FFFFFF = 4.5:1 ✅
   - #1F2A44 на #FFFFFF = 12.6:1 ✅
   - #4B5C7A на #FFFFFF = 6.2:1 ✅
2. Ручной accessibility audit через axe-core
3. Тестирование с реальными пользователями (если возможно)

**Rollback Plan:**

- Если проблемы обнаружены: hotfix конкретных цветовых комбинаций
- Критические проблемы: полный rollback до исправления

---

## Definition of Done

### Epic 14 считается завершённым когда:

**Story Completion:**

- [x] Story 14.1: Design System & CSS tokens — Completed ✅
- [x] Story 14.2: UI Kit components refactor — Completed ✅
- [x] Story 14.3: Page-level components — Completed ✅
- [x] Story 14.4: Documentation sync — Completed ✅
- [x] Story 14.5: Testing & deployment — Completed ✅

**Technical Validation:**

- [ ] Все unit тесты проходят (100% pass rate)
- [ ] Visual snapshot тесты обновлены и проходят
- [ ] Accessibility audit: WCAG AA соблюдён
- [ ] PageSpeed >70 на главных страницах (Home, Catalog, Product, Cart)
- [ ] Cross-browser testing пройден (Chrome, Firefox, Safari, Edge)
- [ ] Cross-device testing пройден (Desktop 1920px, Tablet 768px, Mobile 375px)
- [ ] Нет console errors/warnings в браузере
- [ ] Нет хардкод HEX кодов (кроме badge backgrounds)

**Functional Validation:**

- [ ] Существующая функциональность работает без регрессии:
  - [ ] Навигация и роутинг
  - [ ] Формы (регистрация, login, checkout)
  - [ ] Корзина (добавление, удаление, изменение количества)
  - [ ] Каталог (фильтрация, сортировка, пагинация)
  - [ ] Карточка товара (галерея, выбор вариантов, добавление в корзину)
  - [ ] Личный кабинет (все разделы)
  - [ ] Поиск
- [ ] Все интерактивные состояния корректны:
  - [ ] :hover states
  - [ ] :active states
  - [ ] :focus states (особенно формы)
  - [ ] :disabled states

**Business Validation:**

- [ ] Design Lead approval получен (визуальная реализация)
- [ ] Product Owner approval получен (бизнес-требования)
- [ ] QA Team sign-off получен (testing complete)
- [ ] Stakeholder demo проведена успешно

**Documentation:**

- [ ] design-system.json обновлён до v2.1.0
- [ ] front-end-spec.md синхронизирован
- [ ] Story docs Epic 11 обновлены (11.0, 11.1, 11.2)
- [ ] color-scheme-migration.md статус → "Реализовано"
- [ ] Sprint Change Proposal помечен как Completed
- [ ] PROJECT_PROGRESS.md обновлён (Epic 14 = Done)
- [ ] Git changelog детализирован

**Deployment:**

- [ ] Staging deployment успешен
- [ ] Staging smoke tests пройдены
- [ ] Production deployment выполнен
- [ ] Production monitoring (первые 24 часа):
  - [ ] Нет критических ошибок в Sentry/LogRocket
  - [ ] Performance метрики стабильны
  - [ ] Нет жалоб пользователей
- [ ] Rollback plan протестирован и готов

---

## Dependencies & Blockers

### Внешние зависимости

**Требуется для начала:**

- ✅ Epic 11, 12, 13 завершены (подтверждено)
- ✅ Sprint Change Proposal утверждён Product Owner
- ✅ Design Lead approval новой палитры

**Не требуется:**

- ❌ Backend изменения (только frontend)
- ❌ Database миграции
- ❌ API обновления
- ❌ Изменения в 1С интеграции

### Критические блокеры

**Блокеры отсутствуют:**

- Нет параллельных Epic в разработке
- Нет незакоммиченных изменений в UI компонентах
- Нет конфликтов с другими задачами

---

## Timeline & Milestones

**Общая длительность:** 5-7 рабочих дней

### День 1-2: Фундамент (Stories 14.1)

- Обновление design-system.json
- Обновление globals.css
- Валидация и dev server проверка
- **Milestone:** Источники истины обновлены ✅

### День 3-4: Рефакторинг (Stories 14.2, 14.3)

- Рефакторинг UI Kit компонентов (9 файлов)
- Обновление page-level компонентов
- Unit тесты
- Code review
- **Milestone:** Все компоненты используют токены ✅

### День 5: Документация (Story 14.4)

- Обновление front-end-spec.md
- Синхронизация story docs
- Обновление migration doc
- **Milestone:** Документация синхронизирована ✅

### День 6-7: Тестирование и деплой (Story 14.5)

- Автоматизированное тестирование
- Accessibility audit
- Visual regression tests
- Manual QA
- Staging deployment
- Production deployment
- **Milestone:** Epic 14 завершён ✅

---

## Communication Plan

### Stakeholders

| Роль          | Уведомление         | Формат              |
| ------------- | ------------------- | ------------------- |
| Product Owner | Начало + Завершение | Slack + Demo        |
| Design Lead   | Каждая story        | Figma + Screenshots |
| Frontend Team | Daily               | Stand-up + Slack    |
| QA Engineer   | Story 14.5          | Test reports        |
| Backend Team  | FYI                 | Slack announcement  |

### Key Messages

**Kick-off (День 1):**

```
📢 Начинается Epic 14: Миграция цветовой схемы

Сроки: 2025-11-25 до 2025-12-02 (7 дней)
Scope: 5 stories, 21 story points
Влияние: Frontend UI, документация
НЕ влияет на: Backend, API, функциональность

Детали: docs/stories/epic-14/epic-14-color-scheme-migration.md
Вопросы: @john (PM)
```

**Completion (День 7):**

```
✅ Epic 14: Миграция цветовой схемы ЗАВЕРШЕНА

Результаты:
- ✅ Design System v2.1.0 внедрён
- ✅ 9 UI компонентов обновлено
- ✅ Документация синхронизирована
- ✅ Все тесты проходят
- ✅ Production deployment успешен

Staging: [URL]
Production: [URL]
Report: docs/sprint-change-proposal-color-migration.md
```

---

## Technical Notes

### Grep Commands для валидации

```bash
# Поиск оставшегося хардкода цветов
grep -r "#[0-9A-Fa-f]\{6\}" frontend/src/components --include="*.tsx"

# Поиск старых графитовых цветов
grep -r "#1F1F1F\|#3A3A3A\|#3D3D3D" frontend/src --include="*.tsx"

# Поиск Tailwind классов с хардкод цветами
grep -r "bg-\[#\|text-\[#\|border-\[#" frontend/src --include="*.tsx"

# Поиск старых Tailwind классов (потенциальные проблемы)
grep -r "bg-gray-\|text-gray-\|border-gray-" frontend/src --include="*.tsx"
```

### Git Workflow

```bash
# Создание feature branch
git checkout -b feature/epic-14-color-scheme-migration

# Story 14.1 commit
git commit -m "feat(design-system): migrate to blue color scheme v2.1.0

- Update design-system.json to v2.1.0
- Update globals.css CSS variables
- All primary/secondary/accent colors updated
- Neutral scale with blue-gray undertone
- Shadows and focus states updated

Related: docs/sprint-change-proposal-color-migration.md
Story: 14.1
"

# Story 14.2 commit
git commit -m "refactor(ui): migrate all components to blue color scheme

- Button: use primary tokens instead of hardcoded gray
- Badge: update to semantic accent colors (success, warning, danger, promo)
- Checkbox/Toggle: primary for active states
- Tabs/Input: focus states with primary
- Toast: semantic border colors
- All hardcoded HEX replaced with Tailwind tokens

Components updated: 9
Tests: All passing ✅
Story: 14.2
"

# Merge to main
git checkout main
git merge feature/epic-14-color-scheme-migration
git push origin main
```

---

## References

### Key Documents

- [Sprint Change Proposal](../../sprint-change-proposal-color-migration.md) — детальный анализ и план
- [Color Scheme Migration Guide](../../frontend/color-scheme-migration.md) — техническая спецификация миграции
- [Design System JSON](../../frontend/design-system.json) — источник истины для токенов
- [Frontend Specification](../../front-end-spec.md) — UI/UX спецификация

### Related Epics

- Epic 11: Frontend Landing Page (Done) — использует старую палитру, требует обновления docs
- Epic 12: [Название] (Done) — не затронут
- Epic 13: [Название] (Done) — не затронут

### Useful Links

- WCAG Contrast Checker: https://webaim.org/resources/contrastchecker/
- Tailwind CSS 4.0 Docs: https://tailwindcss.com/docs
- Next.js Testing Guide: https://nextjs.org/docs/testing

---

## Version History

| Version | Date       | Author    | Changes                                          |
| ------- | ---------- | --------- | ------------------------------------------------ |
| 1.0     | 2025-11-25 | John (PM) | Initial epic creation for color scheme migration |

---

**Epic Owner:** John 📋 (PM Agent)
**Technical Lead:** Frontend Lead
**QA Lead:** QA Engineer
**Status:** ✅ Ready for Development
**Next Step:** Story 14.1 kickoff → Design System tokens update
