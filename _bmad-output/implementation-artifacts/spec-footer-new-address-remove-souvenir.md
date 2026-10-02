---
title: 'Новый адрес склада и подвал без «Сувенирной продукции»'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'one-shot'
---

# Новый адрес склада и подвал без «Сувенирной продукции»

## Intent

**Problem:** Склад и пункт самовывоза переехали: теперь они на ул. Дзержинского, 131А, 3 этаж, а сайт по-прежнему показывает ул. Коломийцева, 40/1. Кроме того, ссылка подвала на «Сувенирную продукцию» ведёт в категорию, которую выгрузка 1С 01.10.2026 выключила. Страница такой категории отдаёт базовый title каталога и canonical `/catalog`.

**Approach:** Владелец выбрал вариант «везде»: новый адрес «г. Ставрополь, ул. Дзержинского, 131А, 3 этаж» в одну строку, в прежнем формате. Его получили оба подвала, страница доставки, тизер самовывоза на главной, schema.org Organization, метка Яндекс.Карты на `/delivery` и рабочие тексты `docs/frontend/`. Ссылку на сувенирку удалили из подвала синей темы. Тест подвала теперь проверяет, что этой ссылки нет.

## Suggested Review Order

**Адрес в подвалах**

- Блок «Контакты» синей темы, ссылка ведёт на `/delivery#pickup`
  [`Footer.tsx:78`](../../frontend/src/components/layout/Footer.tsx#L78)

- Подвал темы electric, тот же адрес
  [`ElectricFooter.tsx:107`](../../frontend/src/components/layout/ElectricFooter.tsx#L107)

**Ссылка на сувенирку**

- Удалена последняя строка столбца категорий, остальные slug не тронуты
  [`Footer.tsx:43`](../../frontend/src/components/layout/Footer.tsx#L43)

**Адрес пункта самовывоза за пределами подвала**

- Цель ссылки из подвала, раздел `#pickup`
  [`page.tsx:37`](../../frontend/src/app/(blue)/delivery/page.tsx#L37)

- Метка Яндекс.Карты перенесена на ТЦ «Нестеров», координаты по OpenStreetMap
  [`page.tsx:60`](../../frontend/src/app/(blue)/delivery/page.tsx#L60)

- Тизер на главной, здесь адрес без города, как и раньше
  [`DeliveryTeaser.tsx:31`](../../frontend/src/components/home/DeliveryTeaser.tsx#L31)

- streetAddress в разметке Organization, её читают поисковики
  [`organization.ts:49`](../../frontend/src/config/organization.ts#L49)

**Тесты и документация**

- Проверка, что ссылки на сувенирку нет, плюс новый текст адреса
  [`Footer.test.tsx:123`](../../frontend/src/components/layout/__tests__/Footer.test.tsx#L123)

- Тексты адреса в тестах доставки и тизера
  [`page.test.tsx:136`](../../frontend/src/app/(blue)/delivery/__tests__/page.test.tsx#L136)
  [`DeliveryTeaser.test.tsx:51`](../../frontend/src/components/home/__tests__/DeliveryTeaser.test.tsx#L51)

- Текстовый источник контента сайта
  [`text.md:71`](../../docs/frontend/text.md#L71)
