---
title: 'Разворот надписи «Реклама» на баннерах'
type: 'chore'
created: '2026-08-22'
status: 'done'
route: 'one-shot'
---

# Разворот надписи «Реклама» на баннерах

## Intent

**Problem:** Вертикальная метка «Реклама» на маркетинговых баннерах читалась сверху вниз — `writing-mode: vertical-rl` без разворота даёт направление, противоположное принятому для вертикальных подписей у правого края.

**Approach:** Надпись обёрнута в `<span className="rotate-180">` внутри кнопки-триггера. Разворот висит на тексте, а не на кнопке: `rotate` на самом триггере утащил бы за собой скругление `rounded-l-md`, подложку и тап-таргет 44×24, которыми метка прижата к краю баннера.

## Suggested Review Order

**Разворот надписи**

- Собственно правка: разворот на тексте, геометрия кнопки не тронута
  [`AdDisclosure.tsx:216`](../../frontend/src/components/home/AdDisclosure.tsx#L216)

- Контекст: `writing-mode` остался на кнопке, разворот работает поверх него
  [`AdDisclosure.tsx:211`](../../frontend/src/components/home/AdDisclosure.tsx#L211)

**Фиксация поведения**

- Регресс-тест на направление чтения: jsdom не считает Tailwind-стили, поэтому проверяется класс
  [`AdDisclosure.test.tsx:66`](../../frontend/src/components/home/__tests__/AdDisclosure.test.tsx#L66)

**Синхронизация документации**

- Design Notes исходной спеки маркировки: описание метки приведено к фактическому виду
  [`spec-banner-ad-disclosure.md:110`](./spec-banner-ad-disclosure.md#L110)

- Пять пресуществующих дефектов `AdDisclosure`, найденных ревью и вынесенных из объёма
  [`deferred-work.md`](./deferred-work.md)
