---
title: 'Замена логотипа в шапке сайта на OPTISPORT'
type: 'chore'
created: '2026-08-22'
status: 'done'
baseline_commit: '9dc72c99683f5ab642c762ca797d563223fe495e'
review_loop_iteration: 1 # incremented by step-04 before each review loopback
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Шапка сайта показывает логотип старого бренда (`/LOGO-NEW_Freesport.png`), хотя ребрендинг FREESPORT → OPTISPORT уже проведён в метаданных (`SITE_NAME = 'OPTISPORT'`, `frontend/src/utils/seo.ts:12`). Визуальный бренд расходится с текстовым.

**Approach:** Переключить обе шапки на новый бренд-ассет, привести `alt` к каноническому `OPTISPORT`, синхронизировать пропсы `next/image` с реальной пропорцией новых файлов и обновить связанный vitest-тест. Ассета два: тёмный `/LOGO_OPTIsport.png` для светлой шапки и светлый `/LOGO_OPTIsport-b.png` для тёмной electric-темы.

## Boundaries & Constraints

**Always:**
- Логотип — через `next/image`, с сохранением `priority` (LCP-зона).
- Визуальная высота 32 px (`h-8`), ширина авто. Новый файл 1014×101 против старого 1067×101: высота та же, ширина 338 px → 321 px. Вёрстка шапки не должна поехать.
- `alt` = `OPTISPORT` (совпадает с `SITE_NAME`).
- Ассет подбирается под фон шапки: `Header.tsx` стоит на `bg-white` → тёмный вариант; `ElectricHeader.tsx` стоит на `--bg-body: #0f0f0f` → светлый вариант `-b`. Оба файла 1014×101, одинаковая пропорция 10.04.
- Оба PNG изначально untracked — добавить в git.

**Ask First:**
- Любая правка вёрстки шапки помимо самого `<Image>`.
- Добавление ещё каких-либо вариантов логотипа (мобильный, favicon/og-image) сверх пары светлый/тёмный.

**Never:**
- Не удалять `frontend/public/LOGO-NEW_Freesport.png` — на него ссылаются макеты `frontend/public/examples/*.html`.
- Не править `frontend/public/examples/*.html`.
- Не менять `<Image>` на `<img>`; не писать в `alt` дословное «OPTSPORT» с картинки.
- Не расширять ребрендинг на прочие вхождения `FREESPORT` (баннеры, hero, e-mail) — вне scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Основная шапка | Страница `(blue)`, кроме `/` и `/electric*` | `Header` рендерит `src` с `LOGO_OPTIsport` и `alt="OPTISPORT"`, высота 32 px | N/A |
| Шапка electric | `/electric/*` или `/electric-orange-test` | `ElectricHeader` рендерит светлый `/LOGO_OPTIsport-b.png` с тем же alt; белые литеры читаются на `#0f0f0f`; skew и hover-scale сохранены | N/A |
| B2B-пользователь | `isB2BUser === true` | Бейдж «B2B» рядом с логотипом на месте, логотип не обрезан и не смещён | N/A |
| Поиск по alt | `getByAltText('OPTISPORT')` | Находит логотип; `getByAltText('FREESPORT')` — нет | N/A |

</frozen-after-approval>

## Code Map

- `frontend/src/components/layout/Header.tsx` — шапка боевого сайта, `<Image>` стр. 84. GitNexus impact: `risk: LOW`, 0 upstream.
- `frontend/src/components/layout/ElectricHeader.tsx` — шапка `/electric/*`, `<Image>` стр. 33. `risk: LOW`, 0 upstream.
- `frontend/src/components/layout/__tests__/Header.test.tsx:145` — единственная завязка на alt логотипа; в `frontend/e2e/` и `frontend/tests/` завязок нет.
- `frontend/src/components/layout/LayoutWrapper.tsx` — решает, какая шапка рендерится; не менять.
- `frontend/public/LOGO_OPTIsport.png` — тёмный вариант, 1014×101 RGBA: 17 260 красных + 8 773 чёрных непрозрачных пикселя.
- `frontend/public/LOGO_OPTIsport-b.png` — светлый вариант для тёмного фона, 1014×101 RGBA, попиксельно зеркалит первый: те же 17 260 красных, но 8 773 белых.
- `frontend/src/app/(electric)/layout.tsx:1` и `frontend/src/app/electric-orange-test/layout.tsx:1` — оба подключают `globals-electric-orange.css` (`--bg-body: #0f0f0f`); это единственные маршруты с `ElectricHeader`.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/public/LOGO_OPTIsport.png` и `frontend/public/LOGO_OPTIsport-b.png` — `git add` — без этого Docker/CI не увидят ассет и логотип отдаст 404.
- [x] `frontend/src/components/layout/Header.tsx` — стр. 84: `src` → `/LOGO_OPTIsport.png`, `alt` → `OPTISPORT`, `width` `120` → `321` — в проекте `images.unoptimized: true` (`frontend/next.config.ts:25`), поэтому `width`/`height` задают только aspect-ratio для резервирования места; при 120×32 (3.75) вместо фактических 10.04 бронируется неверная ширина и на загрузке возможен CLS.
- [x] `frontend/src/components/layout/ElectricHeader.tsx` — стр. 33: `src` → `/LOGO_OPTIsport-b.png` (светлый вариант — фон шапки `#0f0f0f`), `alt` → `OPTISPORT`, `width` `150` → `321`. `height` остаётся `32`, классы не тронуты.
- [x] `frontend/src/components/layout/__tests__/Header.test.tsx` — в тесте `should render logo` заменено `getByAltText('FREESPORT')` на `getByAltText('OPTISPORT')`.

**Acceptance Criteria:**
- Given собранный фронтенд, when открыта страница `(blue)` кроме главной, then в шапке новый логотип OPTISPORT без искажения пропорций и без сдвига соседних элементов.
- Given страница `/electric/`, when она отрендерена, then её шапка показывает светлый вариант логотипа, все литеры читаются на тёмном фоне, skew и hover работают как прежде.
- Given репозиторий, when выполнен `grep -rn "LOGO-NEW_Freesport" frontend/src`, then совпадений нет.
- Given `npm run test`, when прогнан `Header.test.tsx`, then все тесты зелёные без правок сверх перечисленных.

## Spec Change Log

- **2026-08-22 — итерация 1 (intent_gap).** Находка ревью: новый ассет на 34 % состоит из чисто чёрных пикселей (`#000`, буквы «OPT» и часть стрелки), а `(electric)/layout.tsx` подключает `globals-electric-orange.css` с `--bg-body: #0f0f0f`; на `/electric/*` чёрная половина логотипа сливается с фоном. Старый ассет был сплошным оранжевым и этой проблемы не имел. Триггер соответствует пункту **Ask First** («варианты логотипа для тёмной темы»).
  **Решение человека:** Alex предоставит отдельный светлый вариант логотипа для тёмного фона; `ElectricHeader.tsx` переключается на него, а не на `/LOGO_OPTIsport.png`.
  **Известное плохое состояние, которого избегаем:** мерж ветки с наполовину невидимым логотипом в electric-шапке.
  **KEEP:** правки в `Header.tsx` (боевая шапка, `bg-white`) верны и должны пережить пере-вывод кода — там новый логотип читается корректно; замена `alt` на `OPTISPORT` и синхронный апдейт `Header.test.tsx` также сохраняются.
  **Закрыто 2026-08-22:** Alex предоставил `frontend/public/LOGO_OPTIsport-b.png` — попиксельное зеркало светлого ассета (те же 1014×101 и 26 033 непрозрачных пикселя, чёрные литеры заменены белыми). Подключён в `ElectricHeader.tsx`. Проверено, что `ElectricHeader` рендерится только на тёмных маршрутах: `(electric)/layout.tsx` и `electric-orange-test/layout.tsx` оба импортируют `globals-electric-orange.css`; ветка `isElectricPage` в `LayoutWrapper.tsx:26` недостижима, так как внутри группы `(blue)` маршрутов `/electric*` нет.

## Verification

**Commands:**
- `cd frontend; npx cross-env VITEST=true vitest run src/components/layout/__tests__/Header.test.tsx` — ожидается: все passed.
- `cd frontend; npm run lint` — ожидается: 0 ошибок и warnings.
- `docker compose --env-file .env -f docker/docker-compose.yml restart frontend` — ожидается: контейнер поднялся, страница 200.

**Manual checks:**
- `http://localhost/catalog` — новый логотип, высота как прежде, бейдж B2B не наехал.
- `http://localhost/electric/` и `http://localhost/electric-orange-test` — светлый логотип, часть «OPT» видна на тёмном фоне (главный признак того, что подключён именно `-b`).
- DevTools → Network: запрашиваются прямые `/LOGO_OPTIsport.png` (blue) и `/LOGO_OPTIsport-b.png` (electric), оба 200. Эндпоинт `/_next/image` в проекте не задействован — `images.unoptimized: true`.

## Suggested Review Order

**Выбор ассета под фон шапки**

- Точка входа: боевая шапка на `bg-white` получает тёмный вариант логотипа.
  [`Header.tsx:84`](../../frontend/src/components/layout/Header.tsx#L84)

- Electric-шапка стоит на тёмном фоне, поэтому берёт светлый вариант `-b`.
  [`ElectricHeader.tsx:33`](../../frontend/src/components/layout/ElectricHeader.tsx#L33)

- Причина асимметрии: фон electric-темы почти чёрный, тёмный логотип на нём пропал бы.
  [`globals-electric-orange.css:44`](../../frontend/src/app/globals-electric-orange.css#L44)

**Пропсы next/image**

- `width` приведён к фактической пропорции 10.04 — при `unoptimized` это защита от CLS.
  [`next.config.ts:25`](../../frontend/next.config.ts#L25)

**Поддерживающее**

- Тест логотипа переведён на новый `alt`, совпадающий с `SITE_NAME`.
  [`Header.test.tsx:145`](../../frontend/src/components/layout/__tests__/Header.test.tsx#L145)
