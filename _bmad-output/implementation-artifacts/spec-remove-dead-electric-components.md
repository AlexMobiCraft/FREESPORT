---
title: 'Удаление мёртвых компонентов темы Electric'
type: 'chore'
created: '2026-09-22'
status: 'done'
route: 'one-shot'
---

# Удаление мёртвых компонентов темы Electric

## Intent

**Problem:** После удаления демо-страницы `/electric-orange-test` в стори 41.19 одиннадцать компонентов темы Electric остались без потребителей: `ElectricTabs`, `ElectricHeroBanner`, `ElectricSectionHeader`, `ElectricModal`, `ElectricToast`, `ElectricAccordion`, `ElectricTooltip`, `ElectricTable`, `ElectricFeaturesBlock`, `ElectricCartWidget`, `ElectricSearchResults`. Запись в `deferred-work.md` от 2026-09-17.

**Approach:** Перед удалением проверили потребителей: `grep -rlw` находит только собственные файлы и barrel-реэкспорты, у `gitnexus impact` риск LOW и внешних вызывающих нет. Файлы удалены. Каталоги `Hero`, `SectionHeader`, `Tooltip`, `Table`, `Features`, `Cart`, `Search` удалены целиком. `Tabs/index.ts` реэкспортировал только Electric и тоже удалён: `ui/index.ts` берёт `Tabs` напрямую из `./Tabs/Tabs`. Из barrel-файлов `Modal`, `Toast` и `Accordion` убраны Electric-строки. Компоненты, которые использует тема `/electric`, не тронуты.

## Suggested Review Order

**Barrel-файлы: остались только живые экспорты**

- Удалён `ElectricToast`/`ElectricToastContainer`. `Toast`, `ToastProvider` и `useToast` на месте
  [`Toast/index.ts:1`](../../frontend/src/components/ui/Toast/index.ts#L1)

- Удалён `ElectricModal`, `Modal` остаётся
  [`Modal/index.ts:1`](../../frontend/src/components/ui/Modal/index.ts#L1)

- Удалён `ElectricAccordion`, `Accordion` и `AccordionItem` остаются
  [`Accordion/index.ts:6`](../../frontend/src/components/ui/Accordion/index.ts#L6)

**Почему удаление `Tabs/index.ts` безопасно**

- Корневой barrel импортирует `Tabs` из файла, а не из каталога
  [`ui/index.ts:62`](../../frontend/src/components/ui/index.ts#L62)

**Документация**

- Из описи убраны `Table` и пример `ElectricModal`, в пример поставлен живой `ElectricPagination`
  [`component-inventory-frontend.md:10`](../../docs/component-inventory-frontend.md#L10)

**Удалённые файлы**

- `git show --stat HEAD`: 11 компонентов, `Tabs/index.ts` и 7 целиком удалённых каталогов
