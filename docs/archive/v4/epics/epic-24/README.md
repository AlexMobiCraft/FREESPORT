# Epic 14: Миграция цветовой схемы - Stories Overview

> **Epic Status:** Ready for Development
> **Total Story Points:** 21
> **Duration:** 5-7 рабочих дней

---

## Stories Quick Reference

| Story    | Title                                                                   | Points | Priority    | Status          | Duration  |
| -------- | ----------------------------------------------------------------------- | ------ | ----------- | --------------- | --------- |
| **14.1** | [Design System & CSS Tokens](14.1.design-system-tokens-update.story.md) | 3      | 🔴 Critical | Ready           | 4-6 hours |
| **14.2** | [UI Kit Refactor](14.2.ui-kit-components-refactor.story.md)             | 8      | 🔴 Critical | Blocked by 14.1 | 1.5 days  |
| **14.3** | [Page Components Update](14.3.page-components-update.story.md)          | 3      | 🟠 High     | Blocked by 14.2 | 4-6 hours |
| **14.4** | [Documentation Sync](14.4.documentation-sync.story.md)                  | 5      | 🟡 Medium   | Blocked by 14.3 | 1 day     |
| **14.5** | [Testing & Deployment](14.5.testing-deployment.story.md)                | 2      | 🔴 Critical | Blocked by 14.4 | 1 day     |

---

## Dependencies Flow

```
14.1 (Tokens)
    ↓
14.2 (UI Kit)
    ↓
14.3 (Pages)
    ↓
14.4 (Docs)
    ↓
14.5 (Testing)
    ↓
Epic 14 Complete ✅
```

**Критично:** Stories должны выполняться **строго последовательно** — каждая зависит от предыдущей.

---

## Key Milestones

### Milestone 1: Фундамент (День 1-2)

- ✅ Story 14.1 Complete
- **Deliverable:** design-system.json v2.1.0, обновлённые CSS-переменные

### Milestone 2: Компоненты (День 3-4)

- ✅ Story 14.2 Complete
- ✅ Story 14.3 Complete
- **Deliverable:** Все UI компоненты используют новую палитру

### Milestone 3: Документация (День 5)

- ✅ Story 14.4 Complete
- **Deliverable:** Синхронизированная документация

### Milestone 4: Валидация (День 6-7)

- ✅ Story 14.5 Complete
- **Deliverable:** Production deployment с полным тестированием

---

## Quick Start Guide

### Для начала Epic 14:

1. **Утверждения:**

   ```markdown
   - [ ] Product Owner approval
   - [ ] Design Lead approval новой палитры
   - [ ] Frontend Lead готов к работе
   ```

2. **Подготовка:**

   ```bash
   # Создать feature branch
   git checkout -b feature/epic-14-color-scheme-migration

   # Убедиться что Epic 11-13 завершены
   git log --oneline | grep "epic-11\|epic-12\|epic-13"
   ```

3. **Kick-off Meeting:**
   - Обзор Sprint Change Proposal
   - Распределение ответственности за stories
   - Подтверждение timeline (5-7 дней)

4. **Начать Story 14.1:**
   - Открыть [14.1.design-system-tokens-update.story.md](14.1.design-system-tokens-update.story.md)
   - Следовать AC и Tasks

---

## Components Impact Matrix

### Автоматически обновятся (через токены):

- ✅ SearchFilters Chip (уже использует `bg-primary`)
- ✅ ProductGallery Thumbnails (уже использует `border-primary`)
- ✅ ProductSummary CTA (уже использует Button component)
- ✅ Navigation active state (уже использует `text-primary`)

### Требуют ручного рефакторинга (Story 14.2-14.3):

- ⚠️ **Button** - хардкод в variant classes
- ⚠️ **Badge** - хардкод всех цветов вариантов
- ⚠️ **Checkbox** - хардкод checked state
- ⚠️ **Toggle** - хардкод track ON color
- ⚠️ **Pagination** - хардкод active page bg
- ⚠️ **Header** - хардкод cart badge
- ⚠️ **Tabs** - хардкод active text
- ⚠️ **Toast** - хардкод border colors
- ⚠️ **Input** - хардкод focus states

**Total:** 9 компонентов требуют обновления

---

## Testing Strategy

### Story 14.1 (Tokens):

- JSON validation
- CSS compilation
- Dev server start
- Visual spot check

### Story 14.2-14.3 (Components):

- Unit tests (per component)
- Visual check (all variants)
- Interactive states (hover, focus, active)

### Story 14.5 (Comprehensive):

- ✅ Unit tests (100%)
- ✅ Snapshot tests (updated)
- ✅ Accessibility audit (WCAG AA)
- ✅ Visual regression (3 breakpoints)
- ✅ Manual QA (4 browsers)
- ✅ Cross-device (Desktop, Tablet, Mobile)

---

## Rollback Plan

**Если что-то пойдёт не так:**

```bash
# Немедленный rollback
git revert <commit-sha-story-14.1>
git revert <commit-sha-story-14.2>
# ... и т.д.

# Deploy previous version
git push origin main
# CI/CD автоматически развернёт

# Время rollback: ~15 минут
```

**Backup файлы** (создаются в Story 14.1):

- `design-system.json.v2.0.0.backup`
- `globals.css.backup`

---

## Communication

### Daily Updates:

- **Slack channel:** #epic-14-color-migration
- **Stand-up:** Ежедневно 10:00
- **Status format:**
  ```
  ✅ Completed: Story 14.X
  🔄 In Progress: Story 14.Y (50%)
  📋 Next: Story 14.Z
  ⚠️ Blockers: None
  ```

### Stakeholder Reports:

- **Product Owner:** Начало + Завершение
- **Design Lead:** После каждой story (screenshots)
- **QA Team:** Story 14.5 (test reports)

---

## Success Criteria (Epic Level)

Epic 14 завершён когда:

**All Stories:**

- [ ] 14.1, 14.2, 14.3, 14.4, 14.5 = Status: Done

**Technical:**

- [ ] Все тесты проходят (100%)
- [ ] WCAG AA соблюдён
- [ ] PageSpeed >70
- [ ] Production deployment успешен

**Business:**

- [ ] Stakeholder approvals получены
- [ ] Нет регрессии функциональности
- [ ] Визуальная реализация соответствует design

---

## Resources

### Documentation:

- [Epic 14 Overview](epic-14-color-scheme-migration.md)
- [Sprint Change Proposal](../../sprint-change-proposal-color-migration.md)
- [Color Migration Guide](../../frontend/color-scheme-migration.md)

### Code:

- [design-system.json](../../frontend/design-system.json)
- [globals.css](../../frontend/src/app/globals.css)
- [UI Components](../../../frontend/src/components/ui/)

### Tools:

- [WCAG Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [JSON Validator](https://jsonlint.com/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)

---

**Last Updated:** 2025-11-25
**Epic Owner:** John 📋 (PM Agent)
**Status:** ✅ Ready for Development
