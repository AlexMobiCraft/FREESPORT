---
title: "Переименование фильтра «Бренд» в «Торговая марка» на странице каталога"
type: "feature"
created: "2026-09-16"
status: "done"
route: "one-shot"
context: []
---

## Intent

**Problem:** В блоке фильтров страницы `/catalog` секция выбора брендов подписана «Бренд», а требуется термин «Торговая марка».

**Approach:** Точечная замена видимых подписей в сайдбаре каталога (`(blue)`-тема): заголовок секции и текст пустого состояния. Плюс обновление ожиданий в тесте страницы.

## Suggested Review Order

- Единственный видимый заголовок секции фильтра — новая подпись «Торговая марка».
  [`CatalogPageClient.tsx:1670`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1670)

- Текст пустого состояния внутри той же секции приведён к единой терминологии.
  [`CatalogPageClient.tsx:1693`](../../frontend/src/app/(blue)/catalog/CatalogPageClient.tsx#L1693)

- Тест доступности ищет кнопку секции по новому имени.
  [`CatalogPage.test.tsx:491`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L491)

- Два теста пустого состояния обновлены под новый текст.
  [`CatalogPage.test.tsx:715`](../../frontend/src/app/(blue)/catalog/__tests__/CatalogPage.test.tsx#L715)
