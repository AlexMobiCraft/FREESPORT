# Story 41.16 — Доказательства исполнения (DEV-часть)

Дата: 15.09.2026. Окружение: локальный dev-стек Docker (`freesport-frontend` :3000, `freesport-backend` :8001, PostgreSQL/Redis). Baseline: `80eba24`. Анонимный доступ, без cookie — проверки выполнены `curl`/Vitest без сессии.

## Команды и итоговые exit codes

| Проверка | Команда | Итог |
|---|---|---|
| Vitest (затронутые файлы) | `docker compose exec frontend npx vitest run <25 файлов>` | 492 теста; после исправления assertions — все зелёные |
| Vitest HitsSection | `docker compose exec -e NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1 frontend npx vitest run HitsSection.test.tsx` | 6/6 passed, exit 0 |
| ESLint | `docker compose exec frontend npm run lint` (`--max-warnings=0`) | exit 0, без warnings |
| TypeScript | `docker compose exec frontend npx tsc --noEmit` | exit 0 |
| Production build | `docker compose exec -e NODE_ENV=production frontend npm run build` | exit 0, 41 маршрут сгенерирован |
| Django checks | `manage.py check` в контейнере backend | 0 issues |
| Миграции | `makemigrations --check` → «No changes detected»; `migrate users 0022` | applied OK |
| Backend-тесты | test-compose `pytest -x -q apps/users apps/bonuses` | 126 passed, exit 0 |
| OpenAPI sync | `manage.py check_openapi_sync` | OK |
| Frontend-типы | `npm run generate:types` | `api.generated.ts` обновлён |
| GitNexus | `detect-changes --scope all` | 45 файлов, 55 символов, 31 процесс, risk=critical (ширина графа `ProductBadge`/`determineBadge`; правки — только строки-лейблы) |

Особенности прогонов:

- Первый Vitest-прогон показал 5 падений: 2 — не обновлённый assertion `'Хит'` в `ProductBadge.test.tsx` (исправлено на `'Лидер продаж'`), 3 — `HitsSection`: MSW-хендлеры читают `NEXT_PUBLIC_API_URL` в момент импорта (до присвоений `vitest.setup.ts`), в контейнере переменная = `http://localhost/api/v1` (nginx), а запросы идут на `localhost:8001` → pass-through → ECONNREFUSED. Артефакт окружения, не регрессия: на хосте тесты проходили (`vitest_verbose*.txt`), в контейнере — зелёные при явном `-e NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`.
- `next build` с `NODE_ENV=development` (значение контейнера) падает на пререндере `/404` (`<Html> should not be imported outside of pages/_document`) — известный артефакт сборки в dev-контейнере; с `NODE_ENV=production` сборка успешна.
- Регенерация `docs/api/openapi.yaml` подтянула дрейф схемы, закоммиченной ранее: endpoint `/newsletter/unsubscribe/one-click/{token}/` теперь описывает GET и POST — код `@api_view(["GET", "POST"])` (`apps/common/views.py:726`) уже принимал оба; также переставлен порядок методов `users_addresses`. Это синхронизация с фактическим кодом, `check_openapi_sync` — OK. Единственное смысловое изменение для E05: description `country` «…на менеджера» → «…на специалиста».

## HTML-доказательства (dev-сервер, серверный HTML через curl)

| URL | Проверено | Результат |
|---|---|---|
| `/electric` | «Лидеры продаж» | ✅ присутствует в SSR HTML |
| `/blog` | «Статьи» | ✅ 11 вхождений; «Блог» в видимом тексте нет |
| `/electric/blog` | «Статьи» | ✅ 7 вхождений |
| `/partners` | «Персональный специалист» / «менеджер» | ✅ «Персональный специалист» + 10 «специалист»; «менеджер» нет |
| `/electric/partners` | то же | ✅ «Персональный специалист» + 4 «специалист»; «менеджер» нет |
| `/home`, `/catalog`, `/b2b-register`, `/search` | клиентский рендер | HTTP 200, ошибок компиляции/рантайма в логах frontend нет; строки покрыты Vitest; живой preview открыт для визуальной проверки |

## Остаточные вхождения (зафиксированы, не заменены)

- E04: «блог/Блог» — только комментарии/JSDoc (`blogService.ts`, `sitemap.ts`, `SubscribeNewsSection.tsx`, комментарий секции в `electric/page.tsx`); slug `/blog`, API `/api/v1/blog/`, имена компонентов сохранены по решению.
- E05: «менеджер» — только комментарии/JSX-комментарии (`authSchemas.ts`, `RegisterForm.tsx`, `AdDisclosure.tsx`, partners pages); видимые строки заменены.
- E08: «Хиты продаж» осталось в backend-описании API-параметра `is_hit` (`apps/products/filters.py:174` help_text, `apps/products/views.py:142` OpenApiParameter) и в JSDoc/моках frontend. В утверждённый список UI-замен не входило (решение: «Query `is_hit`, поле API и логика не меняются») — оставлено осознанно, это техническое описание параметра в Swagger, а не текст публичной страницы.
- E10: label «Email» в `ProfileForm.tsx` (профиль, авторизованная зона) — подзапись E10.1, решение Alex 15.09.2026 «заменить»: label → «Электронная почта», подсказка → «Электронную почту нельзя изменить». Проверено: `npx vitest run src/components/business/ProfileForm` — 11 passed, 2 skipped, exit 0. Тестовые фикстуры `label="Email"` в `Input.test.tsx`/`PasswordInput.test.tsx` — не публичные строки.
- E01/E02: исторические, свежая перепроверка — доступные имена навигации подтверждены чтением кода и Vitest; API политики проверялся 15.09.2026.

## CMS-часть (Alex, вне объёма кода)

- E06 — ✅ выполнено 15.09.2026 (Alex, админка prod). Проверка: `GET https://optisport.ru/api/v1/pages/privacy-policy/` — «Техническая служба Лицензиара» (п. 5.3), старой фразы нет; `GET https://optisport.ru/privacy-policy` после ревалидации ISR — «Техническая служба Лицензиара (Терещенко…)». Авторевалидация `post_save` → `/api/revalidate` отработала.
- E09 — «No Brand»: проверка prod БД 15.09.2026 выявила, что исходный id=37 удалён, действующий «No Brand» — id=40 (`is_active=true`, 1 товар id=12643 «Трико борцовское BoyBo синее», brand_id=40), маппинга нулевого UUID `00000000-…` нет. Решение Alex: merge id=40 → BoyBo (id=1) действием админки «Объединить выбранные бренды»; нулевой UUID → «Без ТМ» (id=38) — fallback кода (`83c5a244`, PR #182) закрепит при следующем импорте. Проверка после правки: `GET /api/v1/brands/` без «No Brand», товар id=12643 → brand_id=1, маппинг → id=38.
- E11 — ✅ выполнено 15.09.2026 (Alex, админка prod). Excerpt `common_blogpost` (slug `obzor-novoj-linejki-odezhdy-dlya-jogi`): «…идеально подходит для повседневного спортивного стиля.» Проверка: `GET /api/v1/blog/` — новый текст, «athleisure» отсутствует; `GET https://optisport.ru/blog/obzor-novoj-linejki-odezhdy-dlya-jogi` после ревалидации ISR — «повседневного спортивного стиля» присутствует, «athleisure» нет. `/electric/blog/<slug>` — 404 (отдельных страниц статей в electric-теме нет, вне объёма).
