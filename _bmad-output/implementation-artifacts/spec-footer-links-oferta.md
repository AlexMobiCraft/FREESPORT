---
title: 'Ссылка на пользовательское соглашение в подвале, удаление пункта «Розница»'
type: 'chore'
created: '2026-08-22'
status: 'done'
route: 'one-shot'
---

# Ссылка на пользовательское соглашение в подвале, удаление пункта «Розница»

## Intent

**Problem:** В подвале сайта не было ссылки на пользовательское соглашение (`/oferta`), при этом в колонке «Клиентам» висел пункт «Розница», ведущий на главную (`/home`) и не несущий смысла.

**Approach:** Правка `DEFAULT_COLUMNS` в `Footer.tsx`: пункт «Пользовательское соглашение» → `/oferta` добавлен в конец колонки «Компания», пункт «Розница» из колонки «Клиентам» удалён. Страница `/oferta` уже существует как опубликованная CMS-запись и обслуживается catch-all `(blue)/[slug]`. Дополнительно закрыт тот же линк-заглушка `href="#"` в `ElectricFooter.tsx` и добавлено регрессионное покрытие с привязкой к колонке.

## Suggested Review Order

1. [`Footer.tsx` — колонки «Компания» и «Клиентам»](../../frontend/src/components/layout/Footer.tsx#L46) — суть правки: две строки в `DEFAULT_COLUMNS`.
2. [`Footer.test.tsx` — новые проверки](../../frontend/src/components/layout/__tests__/Footer.test.tsx#L86) — привязаны к колонке через `within`, негативный тест защищён от вакуумного прохода.
3. [`ElectricFooter.tsx` — линк-заглушка](../../frontend/src/components/layout/ElectricFooter.tsx#L142) — `href="#"` → `/oferta` в экспериментальной теме; проверить, что расширение объёма приемлемо.
4. [`deferred-work.md` — шесть отложенных находок](./deferred-work.md) — мёртвый `/returns`, «Памятка клиенту» → `/home`, дубль `/delivery`, остатки бренда FREESPORT, разнобой в обслуживании юридических страниц, дубли в sitemap.

## Verification

**Commands:**
- `cd frontend; npx vitest run src/components/layout/__tests__/Footer.test.tsx` -- ожидается: 43/43 passed
- `cd frontend; npx tsc --noEmit` -- ожидается: 0 ошибок
- `cd frontend; npx eslint src/components/layout/Footer.tsx src/components/layout/ElectricFooter.tsx src/components/layout/__tests__/Footer.test.tsx` -- ожидается: чисто

**Manual checks:**
- После `docker compose --env-file .env -f docker/docker-compose.yml restart frontend` открыть подвал: в «Компания» четыре пункта, последний ведёт на `/oferta` и отдаёт текст оферты; в «Клиентам» четыре пункта без «Розницы».
