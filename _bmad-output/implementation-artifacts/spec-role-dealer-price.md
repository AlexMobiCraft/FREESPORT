---
title: 'Роль «Дилер» с ценой «Дилерская цена» из 1С'
type: 'feature'
created: '2026-11-16'
status: 'done'
baseline_commit: '940d0fed0a3188d54ebd7509bcfe6986d265852f'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-roles-vip-special-price.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В 1С есть вид цен «Дилерская цена» (GUID `190b6b22-bcac-11ea-81c4-00155d3cae02`, задан на ~71 % товаров `test_base`, прод не считался), но на сайте нет ни роли, ни поля для него. В выгрузку БУС он пока не входит (на проде в `price_types` 11 видов без него), а если войдёт сейчас — импорт создаст `PriceType` с пустым полем, цена потеряется с warning.

**Approach:** Новая B2B-роль `dealer` («Дилер») и поле варианта `dealer_price` («Дилерская цена») по образцу ролей `vip` и `special_price` (`spec-roles-vip-special-price.md`): парсер, импорт, цепочка цены, фильтры, корзина, заказ, экспорт в 1С, админка, баннеры и фронтенд знают роль. Наборы «ролей с ценой из 1С» и «цен, которые импорт снимает» в backend сводятся к константам `pricing_policy.py`, чтобы следующая роль не требовала правок в разрозненных местах. В 1С меняется только белый список выгрузки БУС («Выгрузка информации о товарах» → «Цены») — вручную владельцем.

Решения владельца (2026-11-16):
- **Нет дилерской цены → «Опт 1», затем розница** (как «Спец цена»). По `test_base` дилерская цена задана на 71 % товаров.
- **Цену сняли в 1С → поле сбрасывается** (как «Спец цена»): поле в админке только для чтения и не пишется полным сохранением варианта.
- Остальное — как у VIP: акция `min(цена роли, акционная)` и бейдж «Акция» только при применённой акции (уже общее, правок нет); оплата как у оптовиков (банковский перевод и оплата при получении); баннеры `show_to_wholesale`; РРЦ/МРЦ видны; саморегистрации нет — роль назначает менеджер или 1С по виду цен соглашения (`PriceType.user_role`); сырую `dealer_price` API не отдаёт.

## Boundaries & Constraints

**Always:**
- **Цепочка:** `dealer_price` → `opt1_price` → розница; цена «задана», только если `> 0`. Цепочка живёт только в `pricing_policy.py`, её читают расчёт цены и ценовые фильтры.
- **Парсер:** точное название «Дилерская цена» после `strip()` без учёта регистра → `dealer_price`. «ДИЛЕР +НДС» (есть в 1С с пометкой удаления) и прочие похожие — не опознаются, warning.
- **Роль у `PriceType`:** первая выгрузка с видом «Дилерская цена» создаёт `PriceType` с `product_field=dealer_price` и `user_role=dealer`; запись с пустыми полем и ролью дописывается (`process_price_types`).
- **Смена роли по соглашению** — штатный механизм (`users/services/processor.py:_resolve_role_change`): привязанный аккаунт с видом цен соглашения «Дилерская цена» переходит в `dealer` при следующем обмене контрагентами, даже если сейчас он опт 2–4. На 16.11.2026 таких аккаунтов 0: на проде `onec_price_type_id` пуст у всех 5318 пользователей, в `test_base` соглашений с этим видом нет.
- **Сброс** — тем же механизмом, что спеццена, для каждого поля из набора снимаемых цен: предложение пришло в пакете цен, активный вид поля в справочнике есть, а в предложении ни одного активного вида нет → `NULL`; цена `≤ 0` → `NULL`; две цены одного поля в предложении → вид с поздним `created_at` (при равенстве — больший `pk`), warning «Две цены {поле} в одном предложении: артикул …, виды цен и цены: …» с названием вида 1С из `EXACT_PRICE_TYPE_NAMES`, `stats["warnings"] += 1`; предложения вне пакета не трогаются; сброс — после остальных цен.
- **Один источник наборов:** `PRICE_TYPE_ROLES` в `pricing_policy.py`; из него выводятся скрытые поля API, роли без саморегистрации, оптовые баннеры и проверка оплаты. Набор снимаемых цен (`special_price`, `dealer_price`) управляет импортом, `_skip_derived_field` и `readonly_fields` админки.
- **SSR:** `dealer` в `validRoles` `server-auth.ts` — иначе дилер при серверной отрисовке видит розницу (ошибка, найденная на VIP).
- **Экспорт заказа:** вид цены строки — по полю-источнику (`order_create._price_type_for_field`): «Дилерская цена» или «Опт 1» при откате, без правок экспорта.

**Never:**
- Не трогать `PRICE_TYPE_BY_ROLE` и `order_export.py`, правила акции (`promo.py`), снимки цен корзины, сортировку по цене, `is_wholesale_user` / `wholesale_level`.
- Не трогать саморегистрацию на фронтенде (`authSchemas.ts`), поиск и избранное с ролью `retail`.
- Не создавать синтетические XML: в `data/import_1c` вида «Дилерская цена» нет, импорт — юнит-тесты на словарях.
- Не чинить отложенное с VIP (Electric `HitsSection` с розницей, МРЦ на странице товара, раздел «Акции» по `is_promo`) и известное поведение, общее со спецценой и VIP: импорт включает выключенный товар, у которого положительна только `dealer_price` (`priced_variant_q` в `_enable_priced_product`), и гость видит `0.00`; при двух активных видах «Дилерская цена» заказ пишет в `ВидЦены` первый по `onec_name, pk` (`order_create.py:261`), а импорт берёт цену вида с поздним `created_at`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Дилер с ценой | `dealer_price`=520, опт 1=570, розница=1000 | Платит 520 | N/A |
| Нет дилерской | `dealer_price` NULL или 0, опт 1=570 | Платит 570; `ВидЦены` строки «Опт 1» | N/A |
| Нет ни дилерской, ни опт 1 | оба NULL | Платит розницу | N/A |
| Не верифицирован | роль `dealer`, `is_verified=False` | Платит розницу | N/A |
| Акция ниже / выше | `dealer_price`=520, акция 480 / 600 | 480 с бейджем «Акция» / 520 без бейджа и зачёркивания | N/A |
| Фильтр цены | `dealer_price` NULL, опт 1=570, `max_price`=600 | Товар в выдаче | N/A |
| Новый вид цен | «Дилерская цена» в импорте | `PriceType`: `product_field=dealer_price`, `user_role=dealer` | N/A |
| Похожее название | «ДИЛЕР +НДС», «Дилерская» | Не опознан, цена пропущена | Warning |
| Цену убрали в 1С | пакет цен без «Дилерской цены», у варианта 520 | `dealer_price=NULL`, дальше опт 1 | N/A |
| Нет в пакете | предложения нет в пакете цен | `dealer_price` не меняется | N/A |
| Две цены | старый вид 520, новый (позже `created_at`) 540 | `dealer_price=540` | Warning |
| Старый экземпляр | админка сохраняет вариант после сброса импортом | `dealer_price` остаётся NULL | N/A |
| Соглашение 1С | вид цен соглашения «Дилерская цена» | Привязанный аккаунт получает роль `dealer` (из `unregistered` и из назначенной роли) | N/A |
| Заказ | строка с `dealer_price` | `ВидЦены` строки «Дилерская цена» | Нет активного `PriceType` — warning, как сейчас |
| Оплата картой / саморегистрация | роль `dealer` | Отказ | Как у `vip` |
| Ответы API | каталог, заказ | Поля `dealer_price` нет | N/A |

</frozen-after-approval>

## Code Map

Образец — каждое место с `vip` / `special_price` (`git grep -n -i -E "vip|special_price" -- backend frontend/src`).

- `backend/apps/products/pricing_policy.py:26-77` -- карты ролей. Добавить `dealer` в `ROLE_PRICE_FIELDS`, `PRICE_TYPE_ROLES`, `ROLE_PRICE_FALLBACKS` (`opt1_price`), `INFO_PRICE_ROLES`; `ASSIGNED_PRICE_ROLES = frozenset(PRICE_TYPE_ROLES.values())`; `HIDDEN_ROLE_PRICE_FIELDS = tuple(PRICE_TYPE_ROLES)`; `SPECIAL_PRICE_FIELD` → `RESETTABLE_ROLE_PRICE_FIELDS = ("special_price", "dealer_price")`.
- `backend/apps/products/services/variant_import.py:29,1998-2002,2064,2131` -- `_resolve_special_price` → по полю (вызывать для каждого из `RESETTABLE_ROLE_PRICE_FIELDS`), `_map_offer_prices` пропускает весь набор; текст warning без «СПЕЦЦЕНА». `:1600,1907` — `dealer_price=None`; `:2740` роль подхватится из `PRICE_TYPE_ROLES`. Impact LOW (вызывающий — `import_products_from_1c`).
- `backend/apps/products/models.py:28,942,1196,1423,1446` -- choice `PriceType.product_field`, поле `dealer_price` (null, CHECK `≥ 0`), `_skip_derived_field(self, …, "promo_price", *RESETTABLE_ROLE_PRICE_FIELDS)`; миграция `products/0060_*`. `RESETTABLE_ROLE_PRICE_FIELDS` импортировать в `ProductVariant.save` лениво (как `models.py:1527`): `pricing_policy` ссылается на `products.models` под `TYPE_CHECKING`, импорт на уровне модуля даст третий цикл в `check --cycles`.
- `backend/apps/products/admin.py:709,744` -- `readonly_fields` и fieldset.
- `backend/apps/products/serializers.py:463` -- `priced_variant_q`: `Q(dealer_price__gt=0)`.
- `backend/apps/products/services/parser.py:20,631` -- `EXACT_PRICE_TYPE_NAMES["Дилерская цена"]`, текст warning.
- `backend/apps/users/models.py:141,158,188` -- `get_role_display`, `ROLE_CHOICES`, `B2B_ROLES`; миграция `users/0028_*`. `users/admin.py:969` -- цвет роли. Формы и списки ролей (`products/forms.py:65`, `ASSIGNABLE_ROLE_CHOICES`, кэш баннеров `banners/services.py:32`, `link_1c_customer`, `verify_b2b_application`, письма через `get_role_display`) берут роли из `ROLE_CHOICES` сами.
- `backend/apps/users/serializers.py:46` `ASSIGNED_ROLES`, `banners/models.py:27` `WHOLESALE_LIKE_ROLES` (читает и `banners/services.py:140`), `orders/serializers.py:256` -- через `ASSIGNED_PRICE_ROLES`. Новый импорт `users`/`banners` → `products.pricing_policy`: проверить `check --cycles`.
- `backend/apps/products/factories.py:100,158`, `backend/tests/factories.py`.
- `docs/api/openapi.yaml:5301,5314`, `frontend/src/types/api.generated.ts` (`npm run generate:types`).
- `frontend/src/utils/pricing.ts:17,38,49,102` -- `UserRole`, `isB2BRole` (impact HIGH: вызывающий `ProductCard`, сетки главной, каталога, поиска), `isApiPricedRole`, `getPriceForRole`.
- `frontend/src/types/api.ts:22`, `types/index.ts:29`, `stores/authStore.ts:141`, `utils/server-auth.ts:49`, `ProductCard.tsx:134` (`getProductPrice`, impact HIGH), `ProductInfo.tsx:79`, `CatalogPageClient.tsx:505`, `home/{Hits,NewArrivals,Promo,Sale}Section.tsx` -- `'dealer'` рядом с `'vip'`. `HeroSection.tsx:102`, `ElectricHeroSection.tsx:139` -- пару литералов `vip` / `special_price` заменить на `isApiPricedRole(user?.role)`.
- Без правок: `order_create.py:242`, `cart/*`, `filters.py`, привязка контрагентов 1С.

## Tasks & Acceptance

**Execution:**
- [x] `pricing_policy.py` -- карты, `ASSIGNED_PRICE_ROLES`, `RESETTABLE_ROLE_PRICE_FIELDS`, производный `HIDDEN_ROLE_PRICE_FIELDS`.
- [x] `users/models.py` + `0028`, `users/serializers.py`, `banners/models.py`, `orders/serializers.py`, `users/admin.py` -- роль и наборы.
- [x] `products/models.py` + `0060`, `admin.py`, `serializers.py`, `parser.py`, `variant_import.py`, фабрики -- поле, защита сохранения, распознавание, сброс.
- [x] `openapi.yaml`, `api.generated.ts` -- enum.
- [x] frontend -- типы, `pricing.ts`, `authStore.ts`, `server-auth.ts`, карточка, `ProductInfo`, герои, секции главной, каталог.
- [x] тесты -- параметризовать VIP- и спеццена-тесты ролью `dealer`:
  - цена и каталог: `test_pricing_policy.py`, `test_price_logic.py`, `test_promo_price.py` (`test_list_shows_variant_with_only_role_price`, `TestStaleVariantSaveKeepsSpecialPrice`), `test_catalog_price_filters.py`, `test_catalog_price_visibility.py:377` (не верифицирован, нет поля в ответе);
  - импорт: `test_special_price_import.py` (сброс, две цены — подстрока warning с именем поля), `test_parser_helpers.py`, `test_price_type_role.py`;
  - роль: `test_user_models.py`, `test_user_serializers.py` и `test_user_api.py:189,213` (саморегистрация, смена роли в профиле), `test_manager_clients_section.py:997` (`test_choices_have_no_service_roles` сравнивает список целиком), `test_customer_processor.py:817`, `test_link_1c_customer.py:443,461`, `test_link_applies_role_from_1c.py:38`;
  - заказ: `test_cart_order_integration.py` (снимок цены, оплата оптовика `:493`), `test_order_responses_do_not_expose_raw_role_prices`, `test_order_line_price_type.py` (дилер и откат на «Опт 1»), `banners/tests/test_services.py`;
  - frontend: `pricing.test.ts`, `server-auth.test.ts`, `authStore.test.ts:103`, `ProductCard.test.tsx`, `ProductInfo.test.tsx`, `HeroSection.test.tsx`, `ElectricHeroSection.test.tsx`.

**Acceptance Criteria:**
- Given верифицированный дилер с товаром с `dealer_price` в корзине, when оформляет заказ, then `price_snapshot`, `OrderItem.unit_price` и `ЦенаЗаЕдиницу` равны `dealer_price`, а `ВидЦены` строки — «Дилерская цена».
- Given дилер, when открывает каталог и товар (SSR и клиент), then видит свою цену и РРЦ, а не розницу.
- Given данные импорта с видом «Дилерская цена», when прошли `process_price_types` и `update_variant_prices`, then цена записана в `dealer_price`, у `PriceType` роль `dealer`, а пакет без этого вида снимает цену.
- Given соглашение контрагента с видом цен «Дилерская цена», when импортирован контрагент, then у привязанного аккаунта роль `dealer`.
- Given спеццена, when прошёл импорт и сохранение варианта после рефакторинга сброса, then поведение спеццены не изменилось (существующие тесты спеццены зелёные без правок ожиданий).
- Given `check_openapi_sync` и `makemigrations --check`, when запущены, then расхождений нет.

## Implementation Notes

- **Один набор ролей с ценой из 1С — намеренно** (решение владельца 2026-11-16). Каждая роль из `PRICE_TYPE_ROLES` получает оптовые условия: оплата только банковским переводом или при получении, баннеры `show_to_wholesale`, нет саморегистрации, сырое поле цены скрыто в API. Поэтому `ASSIGNED_PRICE_ROLES` и `HIDDEN_ROLE_PRICE_FIELDS` выводятся из `PRICE_TYPE_ROLES`, а не задаются отдельными наборами. Роль с ценой из 1С без оптовых условий — повод развести наборы, а не исключение внутри одного.
- **`ВидЦены` заголовка документа у дилера — «РРЦ»**, как у VIP и спеццены: `PRICE_TYPE_BY_ROLE` роль не знает, и `_get_price_type` отдаёт `DEFAULT_PRICE_TYPE`. Это безвредно: БУС заголовочный `<ВидЦены>` не читает, соглашение фиксированное «Стандартное», а вид цены строки берётся из снимка (`order_create._price_type_for_field`). Не «чинить» добавлением `dealer` в `PRICE_TYPE_BY_ROLE` — это противоречит Never и сторожу FR-40-13 (`test_price_type_role.py:340`).

## Spec Change Log

- 2026-11-16 (party mode, с согласия владельца): Problem — уточнено, что 71 % — цифра `test_base`; в Verification добавлен раздел «Выкат» (порядок код → белый список → полная выгрузка, выгрузку запускает владелец); в Implementation Notes — решение «один набор ролей с ценой из 1С = оптовые условия» и пояснение про заголовочный `ВидЦены` «РРЦ».

## Review Triage Log

Прогон 1 (2026-11-16): blind-hunter, edge-case-hunter, verification-gap, graph-impact.

| # | Слой | Находка | Вердикт | Маршрут | Обоснование |
|---|---|---|---|---|---|
| 1 | blind | Списки ролей на frontend не сведены к константам, `dealer` дописан в ~10 местах | low | defer | Разрозненные списки были до правки; Approach сводит к константам только backend. Следующая роль снова потребует тех же правок. |
| 2 | blind | Нет тестов роли в секциях главной (`Hits`, `NewArrivals`, `Promo`, `Sale`) и `CatalogPageClient` | medium | defer | Тестов на `vip`/`special_price` там тоже нет (`grep` по `__tests__`) — пробел существовал до правки. |
| 3 | blind | Герои выбирают баннер через `isApiPricedRole`, а не через «оптовый» предикат | false | reject | Замену предписывает Code Map; наборы совпадают по решению владельца (Implementation Notes), риск — только для гипотетической будущей роли. |
| 4 | blind | Нет тестов согласованности карт `pricing_policy` / `EXACT_PRICE_TYPE_NAMES` / `priced_variant_q` | low | reject | Расхождение встретится только при добавлении следующей роли; мутационная проверка спеки ловит потерю `dealer` в ключевых местах. |
| 5 | blind, edge | Warning о двух ценах берёт имя вида обратным поиском по `EXACT_PRICE_TYPE_NAMES`, а не `winner.onec_name` | low | reject | Именно так требует Always («с названием вида 1С из `EXACT_PRICE_TYPE_NAMES`»); исправление — правка спеки. |
| 6 | blind | `test_unverified_dealer_pays_retail` делает полный `save()`, который не пишет `dealer_price` | low | patch | Тест держится на значении в памяти и вводит в заблуждение; исправление — удалить строку. |
| 7 | blind | Наборы в тестах литералами, а не из констант | false | reject | Литералы намеренны: тест фиксирует состав набора, импорт константы сделал бы проверку тавтологией. |
| 8 | blind | Имена и docstring тестов остались «special_price» после параметризации `dealer` | low | patch | Прямое переименование без смены ожиданий. |
| 9 | blind | `test_order_responses_do_not_expose_raw_role_prices` переключён на `dealer`, путь `special_price` потерян | medium | patch | Регрессионный путь спеццены в ответе заказа больше не проверялся; прогон по обеим ролям. |
| 10 | blind | `test_offer_outside_of_package_is_untouched` не проверяет сброс у варианта в пакете | low | patch | Одна проверка `inside.dealer_price is None`. |
| 11 | blind | Известное поведение из Never не записано в `deferred-work.md` | low | defer | Расхождение `ВидЦены` (первый по `onec_name, pk`) и цены (поздний `created_at`) при двух активных видах — реальное, запись в deferred-work. |
| 12 | blind | В `docs/` нет ролей с ценой из 1С и порядка выката | low | defer | Пробел существовал для `vip`/`special_price` до правки. |
| 13 | blind | Заглушка `get_role_display` под `TYPE_CHECKING` дублирует карту ролей | low | reject | Существовала до правки, код не исполняется. |
| 14 | blind | GUID «Дилерской цены» литералом в пяти тестовых файлах | low | reject | Тот же стиль, что у соседних GUID; БД чистится между тестами. |
| 15 | blind | Явные `dealer_price=None` при создании варианта | false | reject | Предписано Code Map (`:1600,1907`); исправление — правка спеки. |
| 16 | edge | Ожидание `ROLE_PRICE_FALLBACKS == {...}` изменилось вопреки AC «тесты спеццены без правок ожиданий» | false | reject | Ожидание по спеццене (`role_price_fields("special_price")`) не изменилось; литерал всей карты обязан включить `dealer`. |
| 17 | graph | Индекс GitNexus `stale` (46 незакоммиченных файлов), слой не выполнен | false | reject | Владелец переиндексировал рабочее дерево (`up-to-date`, 982 файла), слой повторён 2026-11-17 — строки 18–19. |
| 18 | graph | `update_variant_prices` / `process_price_types` — граф CRITICAL, Code Map пишет LOW | low | reject | 58 из 59 вызывающих — тесты, рабочий вызывающий один (`import_products_from_1c`), новые ветки покрыты `TestDealerPriceUpdate` / `TestDealerPriceTypes`; исправление — правка спеки. |
| 19 | graph | `priced_variant_q` тянет `visible_brands` / `visible_categories` и goods-импорт — не названы в Never | low | reject | Поведение то же, что у VIP и спеццены (`_enable_priced_product` назван в Never); исправление — правка спеки. |
| — | graph | Несогласованных вызывающих, новых циклов (`check --cycles` = базовая линия) и символов без тестов нет | — | — | — |
| — | verification-gap | Пробелов нет | — | — | — |

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` -- expected: зелёные.
- В том же контейнере: `python manage.py makemigrations --check --dry-run`, `python manage.py check_openapi_sync` -- expected: без изменений и расхождений (рецепт — память `reference_backend_checks_in_container`).
- В `frontend/`: `npm run generate:types` -- expected: дифф `api.generated.ts` только в enum роли (гейт `api-contract.yml`).
- `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"`, `npx gitnexus check --cycles` -- expected: ожидаемые символы; только два базовых цикла.
- В `frontend/`: `npm run format:check`, `npm run lint`, `npx tsc --noEmit`, `npx vitest run` -- expected: без ошибок.
- Линтеры backend — навык `backend-lint`, после зачётного pytest.
- Мутация: убрать `dealer` из `server-auth.ts`, `priced_variant_q`, `ASSIGNED_PRICE_ROLES`, `RESETTABLE_ROLE_PRICE_FIELDS` — новые тесты краснеют.

**Выкат (порядок обязателен):**
1. Код с миграциями `products/0060_*` и `users/0028_*` — на прод.
2. Только после этого владелец добавляет «Дилерская цена» в белый список БУС («Выгрузка информации о товарах» → «Цены»). В обратном порядке импорт создаст `PriceType` с пустым `product_field`, и цены первой волны пропадут с warning: запись потом дозаполнится, но уже прошедшие цены повторно не придут.
3. Владелец сам запускает полную выгрузку. Правка белого списка не регистрирует товары к выгрузке, поэтому без неё дилерские цены придут только с предложениями, которые меняются, а остальные товары до тех пор будут у дилера по «Опт 1».
4. Проверка на проде: у `PriceType` «Дилерская цена» `product_field=dealer_price`, `user_role=dealer`, `is_active=True`; число вариантов с `dealer_price > 0` сопоставимо с долей по 1С.
