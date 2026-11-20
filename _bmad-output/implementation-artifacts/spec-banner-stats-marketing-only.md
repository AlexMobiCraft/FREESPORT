---
title: 'Статистика баннеров: только рекламные баннеры слайдера, без шапки'
type: 'feature'
created: '2026-11-20'
status: 'done'
route: 'dispatch'
baseline_commit: '365bc35221c3ec3d37abaac4936892b60fceee4d'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Доработка спек `spec-banner-impressions-clicks-ord.md` и `spec-banner-stats-period-summary.md`. Счётчик показов и кликов собирает статистику и баннеров шапки (hero, обе темы), хотя для ОРД и маркетинга нужны только маркетинговые баннеры слайдера. Строки шапки засоряют сводку.

**Approach:** Шапка перестаёт отправлять события, сервер отбрасывает события не-маркетинговых баннеров, накопленные строки шапки удаляет data-миграция.

**Decisions (владелец, 20.11.2026):** статистику шапки удалить из базы и в дальнейшем не собирать; оставить только баннеры слайдера (`type = marketing`). Это отменяет правило первой спеки «учитываются все баннеры из API (hero и marketing)».

## Boundaries & Constraints

**Always:**
- Сервер — источник правды: событие баннера с `type != marketing` отбрасывается молча (204), как событие выключенного баннера. Клиенту не доверяем.
- Удаляются только строки, чей баннер сейчас существует и имеет `type = hero`. Строки удалённых баннеров (`banner_id IS NULL`) остаются: тип по снимку не определить (на проде таких строк 0).
- Маркетинговый баннер, переведённый позже в hero, сохраняет строки, собранные, пока он был маркетинговым: это показы рекламы для ОРД.

**Never:**
- Не менять схему `BannerDailyStat`, формат CSV для ОРД, сводку за период и `sync_daily_stat_snapshots`.
- Не трогать учёт `MarketingBannersSection` и `useBannerViewTracking`/`siteEvents` по поведению.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Событие шапки | `POST {events:[{banner_id:<hero>,kind:"view"}]}` | 204, строка не создана | — |
| Пачка смешанная | события hero и marketing | 204, записан только marketing | — |
| Миграция | строки hero, marketing и `banner_id=NULL` | hero удалены, остальные на месте | — |
| Список баннеров в админке | hero-баннер | колонки «Показы / Клики / CTR за 30 дней» — «—» | — |

</frozen-after-approval>

## Code Map

- `backend/apps/banners/services.py` -- `_UPSERT_DAILY_STAT_SQL` (условие `WHERE`), `record_events` (impact LOW, 1 вызывающий — `SiteEventsView`).
- `backend/apps/banners/views.py:156-164` -- `@extend_schema(description=…)` у `site-events`: дописать про баннеры шапки; затем `docs/api/openapi.yaml` и `frontend/src/types/api.generated.ts`.
- `backend/apps/banners/admin.py:199-209` -- `views_30d`, `clicks_30d`, `ctr_30d` у `BannerAdmin` (LOW); `marketing_admin.py` наследует.
- `backend/apps/banners/migrations/0010_sync_banner_daily_stat_snapshots.py` -- образец `RunPython` на уровне модуля с `noop`; новая `0011` зависит от неё.
- `backend/apps/banners/factories.py` -- `BannerFactory` по умолчанию hero (default модели), `MarketingBannerFactory` — marketing.
- `backend/apps/banners/tests/test_site_events.py` (25 × `BannerFactory`, `:103`, `:115` — hero явно), `test_admin.py` (тесты колонок 30 дней), `test_services.py` -- события через `record_events` переводятся на `MarketingBannerFactory`; строки через `make_stat` тип не проверяют.
- `frontend/src/components/home/HeroSection.tsx:18-19,66-75,210,228-232,254-255` и `ElectricHeroSection.tsx:22-23,92-101,202-203,233-240` -- `useBannerViewTracking`, `trackBannerClick`, `sectionElement`/`loadedId` нужны только счётчику. Impact: `ElectricHeroSection` LOW (поток `Home`), `HeroSection` без вызывающих в графе.
- `frontend/src/components/home/__tests__/HeroSection.test.tsx:650-776`, `ElectricHeroSection.test.tsx:187-` -- блоки «показы и клики».
- `frontend/src/hooks/useBannerViewTracking.ts:8-12` -- в JSDoc пример hero-карусели.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/banners/services.py` -- в `WHERE` upsert добавить `AND b.type = %(marketing)s` (значение `Banner.BannerType.MARKETING`); обновить комментарий над SQL и docstring `record_events` -- сервер не пишет статистику шапки.
- [x] `backend/apps/banners/migrations/0011_delete_hero_banner_daily_stats.py` -- `RunPython`: удалить `BannerDailyStat` с `banner__type="hero"` на исторических моделях; обратная — `noop` -- очистка накопленного.
- [x] `backend/apps/banners/admin.py` -- три колонки 30 дней возвращают «—» для не-маркетингового баннера -- в списке нет нулей шапки.
- [x] `backend/apps/banners/views.py` + `docs/api/openapi.yaml` + `frontend/src/types/api.generated.ts` -- в описании: «события баннеров шапки (не `marketing`) отбрасываются» -- гейт контракта API.
- [x] `frontend/src/components/home/{HeroSection,ElectricHeroSection}.tsx` -- убрать хук, `trackBannerClick`, `onAuxClick`, `onLoad`/`onError`-учёт, `sectionElement`/`loadedId` и комментарии про ОРД -- шапка не шлёт события.
- [x] `frontend/src/hooks/useBannerViewTracking.ts` -- JSDoc: пример про один DOM-узел без упоминания hero как места применения -- документация не врёт.
- [x] Тесты backend: матрица I/O (событие hero → нет строки; смешанная пачка; функция миграции с тремя видами строк; колонки «—» у hero и числа у marketing); существующие тесты событий — на `MarketingBannerFactory`. Frontend: блоки «показы и клики» шапок заменить проверкой, что ни показ, ни клик (включая среднюю кнопку) не вызывают `trackBannerView`/`trackBannerClick`.

**Acceptance Criteria:**
- Given шапка с баннером из API видна дольше 1 с и по ней кликнули, then запросов `site-events` нет и строк статистики не появилось.
- Given маркетинговый баннер слайдера виден ≥ 1 с, then показ засчитан, как прежде.
- Given на проде строки hero, when применена миграция, then в сводке `/marketing/banners/bannerdailystat/` баннеров шапки нет, суммы маркетинговых не изменились.

## Implementation Notes

- Миграция 0011 удаляет только строки hero-баннера без ERID и без рекламодателя: шапка не может быть рекламой (`Banner.clean`), поэтому строка с реквизитами собрана, пока баннер был маркетинговым, и нужна для ОРД. Нерекламные строки маркетингового периода у баннера, переведённого в hero, от строк шапки не отличить — они удаляются. На проде 20.11.2026 у hero один баннер (id 3), обе его строки без реквизитов.
- Тесты событий переведены на `MarketingBannerFactory`; для неактивного, просроченного и будущего баннера тип `marketing` задан явно, иначе они отбрасывались бы как hero и тест ничего бы не проверял.

## Spec Change Log

## Review Triage Log

Ревью кода, 20.11.2026, итерация 0 (blind-hunter, edge-case-hunter, verification-gap, graph-impact):
- low → patch: миграция 0011 по `banner__type="hero"` удалила бы рекламные строки баннера, переведённого из слайдера в шапку (blind #1, edge #2, edge claim «суммы маркетинговых не изменились») — на проде таких строк нет (проверено SELECT: обе строки hero без ERID и рекламодателя), фильтр `erid="" и advertiser_name=""` — прямая правка.
- low → patch: в описании `site-events` у шапки нет «молча» (blind #10).
- low, отклонено: сортировка списка баннеров по колонкам 30 дней учитывает скрытые суммы hero (blind #3, edge #1) — после миграции у hero строк нет, суммы 0; лечение — `Case/When` в аннотации.
- low, отклонено: «—» в списке баннеров и цифры в сводке у баннера, переведённого из слайдера в шапку (blind #2) — редкий случай, строки остаются для ОРД по правилу Always.
- low, отклонено: повтор проверки типа и `getattr` в трёх колонках (blind #4) — косметика, вынос — рефакторинг.
- low, отклонено: нет теста возврата `record_events` для hero и смены типа в течение дня (blind #5, #6) — отсутствие строк проверено через HTTP, verification-gap пробелов не нашёл.
- low, отклонено: окно деплоя, когда старый backend пишет события шапки после `migrate` (edge #3) — `deploy.yml:467` выполняет `migrate` в уже новом контейнере, окно — секунды на B2B-трафике; лечение — повторная очистка.
- low, отклонено: строки, собранные, пока баннер был hero, у баннера, ставшего маркетинговым, остаются (edge #4) — на проде hero-строки только у баннера 3, он hero.
- low, отклонено: JSDoc хука описывает режим одного DOM-узла без текущих пользователей (blind #9) — контракт хука не изменился, описание верно.
- false: `banner_type` в снимке (blind #7) — Never запрещает менять схему `BannerDailyStat`.
- false: проверка после выката противоречит правилу (blind #8) — правка спеки этого билда; после патча миграции на проде строк hero не останется (у баннера 3 нет реквизитов).
- false: строки удалённых hero-баннеров остаются в сводке вопреки AC (edge claim) — Always сохраняет их явно, на проде таких строк 0, AC сформулирован для прода.
- false: спеки нет в диффе (blind #11) — спека передана слою edge-case как claims-файл, из diff исключена намеренно.
- verification-gap: пробелов нет.
- graph-impact, первый запуск: индекс помечен stale (HEAD — merge-коммит PR #405 с тем же деревом, что у проиндексированного 953b299) — слой не выполнен; перезапуск после `analyze --force`.
- graph-impact, повтор на diff с патчами: находок нет — `record_events` MEDIUM (единственный вызывающий `SiteEventsView.post` результат не читает), остальные LOW, `useBannerViewTracking`/`trackBannerClick` остались только у слайдера, новых циклов нет (базовая линия из двух).
- low, отклонено (carried, = blind #3): сортировка колонок 30 дней у бывшего маркетингового баннера, ставшего hero, идёт по скрытым суммам (graph-impact, замечание) — влияет только на порядок строк в списке.

## Design Notes

Фильтр и на клиенте, и на сервере: клиент перестаёт тратить запросы, сервер защищает от старых вкладок со старым бандлом (очередь живёт до 5 с, вкладки — часами) и от ручных запросов. Миграция необратима: удалённые строки не восстановить, на проде их 2 (20 показов, 2 клика за 19–20.11.2026).

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend sh -c "python manage.py makemigrations --check --dry-run && pytest -q -p no:sugar apps/banners tests/unit/test_marketing_admin_site.py tests/integration/test_marketing_section.py"` -- expected: миграции не нужны, тесты зелёные.
- После pytest: навык `backend-lint`; `check_openapi_sync` в контейнере; `npm run generate:types` без диффа -- expected: чисто.
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run src/components/home src/hooks src/services` -- expected: без ошибок.

**Manual checks:**
- После выката: `SELECT b.type, count(*) FROM banner_daily_stats s LEFT JOIN banners b ON b.id = s.banner_id GROUP BY 1` — строк `hero` нет.
