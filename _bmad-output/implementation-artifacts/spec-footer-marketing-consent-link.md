---
title: 'Ссылка на «Согласие на получение рекламы» в подвале'
type: 'chore'
created: '2026-09-22'
status: 'done'
route: 'one-shot'
---

# Ссылка на «Согласие на получение рекламы» в подвале

## Intent

**Problem:** Документ «Согласие на получение рекламы» (`/marketing-consent`) открывался только из чекбоксов рассылки в формах. В подвале, в отличие от Политики ПДн, ссылки на него не было.

**Approach:** Добавить ссылку «Согласие на получение рекламы» → `/marketing-consent` в оба подвала сразу после «Политики конфиденциальности»: в колонку «Компания» (`DEFAULT_COLUMNS` в `Footer.tsx`) и в нижнюю панель `ElectricFooter.tsx` с тем же оформлением, что у соседних ссылок. Страница — опубликованная CMS-запись, её обслуживает `(blue)/[slug]`; на проде отдаёт 200.

## Suggested Review Order

1. [`Footer.tsx` — колонка «Компания»](../../frontend/src/components/layout/Footer.tsx#L53) — суть правки, одна строка.
2. [`ElectricFooter.tsx` — нижняя панель](../../frontend/src/components/layout/ElectricFooter.tsx#L159) — новый `Link` скопирован с соседей, включая muted-контраст (этот дефект уже записан в deferred-work).
3. [`Footer.test.tsx` — порядок в колонке](../../frontend/src/components/layout/__tests__/Footer.test.tsx#L133) — проверяет, что ссылка стоит сразу за Политикой.
4. [`ElectricFooter.test.tsx` — ссылки панели](../../frontend/src/components/layout/__tests__/ElectricFooter.test.tsx#L47) — проверка `href`.
