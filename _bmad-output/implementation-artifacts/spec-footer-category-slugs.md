---
title: 'Исправить slug категорий в ссылках подвала'
type: 'bugfix'
created: '2026-09-28'
status: 'done'
route: 'one-shot'
---

# Исправить slug категорий в ссылках подвала

## Intent

**Problem:** Ссылка «Детский транспорт» в подвале открывала каталог без фильтра: slug `detskiy-transport` не совпадает с `Category.slug` на проде (`detskij-transport`). Тот же дефект у «Бассейны, пляж, аксессуары» и «Сувенирная продукция»: транслитерация y/ya вместо j/ja.

**Approach:** Сверить все 12 ссылок колонки «Каталог» с `/api/v1/categories-tree/` прода, заменить три расходящихся slug и закрепить их тестом.

## Suggested Review Order

**Slug ссылок подвала**

- Три slug приведены к `Category.slug` прода: `detskij-transport`, `bassejny-pljazh-aksessuary`, `suvenirnaja-produktsija`.
  [`Footer.tsx:37`](../../frontend/src/components/layout/Footer.tsx#L37)

- Остальные девять slug колонки уже совпадали с продом, их не трогали.
  [`Footer.tsx:42`](../../frontend/src/components/layout/Footer.tsx#L42)

**Тесты**

- `it.each` фиксирует исправленные href трёх ссылок.
  [`Footer.test.tsx:112`](../../frontend/src/components/layout/__tests__/Footer.test.tsx#L112)
