---
title: 'Роли VIP и «Спец цена» с ценами из 1С'
type: 'feature'
created: '2026-10-26'
status: 'done'
baseline_commit: 5147944e7c73b38580660b25f9f9bab50ef6e4ee
route: 'dispatch'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В 1С заведены виды цен «VIP» и «Спец Цена», но на сайте нет ролей, которым они предназначены: парсер такие виды цен не опознаёт (warning, цена теряется), клиентам нечего показать и продать по этим ценам.

**Approach:** Две новые B2B-роли `vip` и `special_price` и два поля варианта `vip_price`, `special_price`. Парсер опознаёт виды цен, импорт кладёт цены в поля, расчёт цены, фильтры каталога, корзина, заказ и фронтенд знают обе роли. В 1С меняется только белый список выгрузки БУС («Выгрузка информации о товарах» → «Цены») — вручную владельцем, без доработки 1С.

Решения владельца (2026-10-26):
- **VIP** ведёт себя как «Опт 1», но со своей ценой `vip_price`. Нет цены VIP → розница (как у всех оптовых ролей).
- **Спец цена:** `special_price`, иначе `opt1_price`, иначе розница. Спеццена применяется как есть, даже если выше «Опт 1».
- **Акция и наименьшая цена — для всех ролей.** Клиент любой роли платит меньшую из цен: свою или акционную, `min(цена по роли, акционная цена)`. **Меняет цену для всех оптовых ролей, а не только для новых:** отменяет пункт решения 2026-10-21 «акция применяется всегда, даже если выше или равна цене клиента». Остальные правила акции без изменений: одна текущая акция, снимки цен в корзине не пересчитываются, зачёркнутая цена показывается только если она выше акционной.
- **Бейдж «Акция»** показывается, только когда акция применена для этого клиента. Если клиент платит свою цену, товар выглядит как без акции.
- **Названия видов цен в 1С неизменны:** «VIP цены» и «СПЕЦЦЕНА». Парсер опознаёт их по точному названию.
- **Оплата:** обе роли — как оптовики, то есть только банковский перевод и оплата при получении (`orders/serializers.py:245`).

## Boundaries & Constraints

**Always:**
- **Одна цепочка цены.** «Поле роли → запасное поле → розница» живёт в `pricing_policy.py`; по ней считают `get_regular_price_for_user` и ценовые фильтры каталога по роли. Цена «задана», только если строго `> 0`.
- **Акция.** `min` считается в `get_price_for_user` и больше нигде: корзина, заказ, API и JSON-LD берут результат оттуда. `min` — среди положительных значений: если цена роли `≤ 0`, платит акцию; если акции нет — цену роли.
- **Роли.** `vip` и `special_price` входят в `User.B2B_ROLES` (верификация, видимость оптовых полей, действия менеджера) и в `INFO_PRICE_ROLES` (РРЦ/МРЦ). Саморегистрации на них нет: `get_self_service_roles()` строится из `B2B_ROLES`, поэтому обе роли вычитаются из него явно; роль назначает менеджер или 1С по виду цен соглашения (`PriceType.user_role`).
- **Подписи:** роли «VIP» и «Спец цена»; `product_field` — «Цена VIP» и «Специальная цена».
- **Парсер** (после проверки акции, до «опт N»): точное совпадение названия после `strip()` и без учёта регистра. «VIP цены» → `vip_price`, «СПЕЦЦЕНА» → `special_price`. Поиск по подстроке для них не применяется: похожие названия («Спец Цена», «VIP») не опознаются. Неопознанное — warning, как сейчас.
- **Роль у `PriceType`.** Если `user_role` пуст, а `product_field` стал `vip_price` / `special_price` (запись создана или раньше имела пустое поле), `user_role` = `vip` / `special_price`. Заранее GUID неизвестны, миграция их не засеет.
- **Снятие спеццены.** Предложение пришло в пакете цен, активный вид `special_price` в справочнике есть, а ни одного активного вида `special_price` в предложении нет → `special_price=NULL`. Сброс применяется после `price_updates`, чтобы не затереть цену нового вида при двух активных. Цена `≤ 0` → NULL. Предложения вне пакета не трогаются. Для `vip_price` — как у «Опт 1…4» (без сброса): VIP-цена задана на всех товарах.
- **Две цены `special_price` в одном предложении** (два активных вида, например после пересоздания вида в 1С) — аномалия. Берётся цена вида с более поздним `PriceType.created_at` (при равенстве — с большим `pk`), в лог импорта пишется warning с артикулом варианта, GUID и ценами обоих видов.
- **Видимость.** Сырые `vip_price` / `special_price` API не отдаёт: клиент получает итог в `current_price` / `regular_price`.
- **Админка.** `special_price` только для чтения (источник истины — 1С, ручную правку сотрёт импорт); `vip_price` правится как `opt1–4`.
- **Баннеры.** Обе роли — как оптовики (`show_to_wholesale`).
- **Карточка и страница товара.** Акция считается применённой, только если `promo_price > 0` и `current_price ≤ promo_price`, по тому же варианту, по которому показана цена. Одно правило (хелпер в `pricing.ts`) управляет бейджем «Акция», зачёркнутой ценой и подписью «Акционная цена». Не применена → оформление как без акции, бейджа «Акция» нет. `is_promo` в API не меняется.
- **Терминология.** В `pricing_policy.py` и `filters.py` слова «специальная цена» про любую цену роли заменяются на «цена роли» (`has_special` → `has_role_price`). «Специальная цена» остаётся только за новым полем `special_price`.

**Never:**
- Не менять экспорт заказа в 1С: вид цен в заказе остаётся по `PRICE_TYPE_BY_ROLE` / `РРЦ` по умолчанию (GUID новых видов цен неизвестны до первой выгрузки; БУС `ВидЦены` строки не читает).
- Не трогать `is_wholesale_user`, `wholesale_level`, сортировку по цене. Фильтры цены акцию не учитывают — как сейчас.
- Не пересчитывать снимки цен в корзине. Не менять правила импорта и активности акции (`promo.py`).
- Не править экраны, где роль зашита как `retail` для всех: поиск (`SearchResults.tsx`, `EmptySearchResults.tsx`) и избранное (`users/serializers.py:798`).
- Не повторять путь `trainer` в карточке: она читает `trainer_price`, которого API не отдаёт.
- Не менять отбор раздела «Акции» (фильтр `is_promo`) и `PromoSection`: они отбирают по флагу товара (записано в deferred-work 2026-10-26 вместе с интеграционным тестом импорта и расхождением `getProductPrice`).
- Не создавать синтетические XML для теста импорта: в реальных выгрузках новых видов цен пока нет, импорт покрывается юнит-тестами на словарях.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| VIP с ценой | `vip_price`=900, опт 1=1000, розница=1200 | Платит 900 | N/A |
| VIP без цены | `vip_price` NULL или 0 | Платит розницу | N/A |
| Спеццена задана | `special_price`=800, опт 1=1000 | Платит 800 | N/A |
| Спеццена выше опт 1 | `special_price`=1100, опт 1=1000 | Платит 1100 | N/A |
| Нет спеццены | `special_price` NULL или 0, опт 1=1000 | Платит 1000 | N/A |
| Нет ни спеццены, ни опт 1 | оба NULL | Платит розницу | N/A |
| Не верифицирован | роль `special_price`, `is_verified=False` | Платит розницу | N/A |
| Акция ниже цены роли | Спеццена 800, акция 700 | Платит 700, 800 зачёркнуто, бейдж «Акция» | N/A |
| Акция выше цены роли | Спеццена 800, акция 900; то же опт 1=700, акция 800 | Платит 800 (700); зачёркнутой цены и бейджа «Акция» нет, оформление как без акции | N/A |
| Акция равна цене | Опт 3=800, акция 800 | Платит 800; акция применена: бейдж «Акция», зачёркнутой цены нет | N/A |
| Розница 0, акция есть | `retail_price`=0, цены роли нет, акция 500 | Платит 500 | N/A |
| Фильтр цены | `special_price` NULL, опт 1=800, `max_price`=900, роль `special_price` | Товар в выдаче | N/A |
| Спеццена убрана в 1С | Пакет цен без вида «СПЕЦЦЕНА», у варианта 800 | `special_price=NULL`, дальше опт 1 | N/A |
| Два активных вида | Старый и новый `special_price`, в предложении цена нового | Цена нового, не сброшена | N/A |
| Обе цены в предложении | Старый вид 800, новый (позже `created_at`) 850 | `special_price=850` | Warning: артикул, оба GUID и цены |
| Нет в пакете | Предложения нет в пакете цен | `special_price` не меняется | N/A |
| Новый вид цен | В данных импорта «СПЕЦЦЕНА» / «VIP цены» | `PriceType` создан; «СПЕЦЦЕНА»: `product_field=special_price`, `user_role=special_price`; «VIP цены»: `product_field=vip_price`, `user_role=vip` | N/A |
| Регистр и пробелы | « vip цены », «Спеццена» | Опознаны | N/A |
| Похожее название | «Спец Цена», «VIP» | Не опознаны, цены пропущены | Warning с подсказкой |
| Запись уже была | `PriceType` с пустыми `product_field` и `user_role` | Поле и роль проставлены | N/A |
| Название не опознано | Вид цен «Особые» | Цены пропущены | Warning с подсказкой |
| Оплата картой | Роль `vip` или `special_price` | Отказ: только банковский перевод и оплата при получении | Как у оптовиков |
| Саморегистрация | `POST /register` с ролью `vip` | Отказ: недопустимая роль | Как для `admin` |

</frozen-after-approval>

## Code Map

- `backend/apps/users/models.py:141,157,181` -- `get_role_display` (stub), `ROLE_CHOICES`, `B2B_ROLES`. Добавить роли; миграция `users/0027_*` (choices; `max_length=20` хватает). Верификация, `_b2b_role_choices`, `link_1c_customer`, `staff_journal` берут роли отсюда сами.
- `backend/apps/users/serializers.py:60`, `views/misc.py:49` -- `get_self_service_roles`: вычесть `vip`, `special_price`.
- `backend/apps/products/pricing_policy.py:24-33,34,45` -- `ROLE_PRICE_FIELDS`, `INFO_PRICE_ROLES`: единственный источник. Добавить запасное поле (`special_price` → `opt1_price`). Комментарии: «специальная цена» → «цена роли».
- `backend/apps/products/models.py:928,1145,1381,1475` -- `PriceType.product_field` choices; образец `opt4_price` и CHECK `products_opt4_price_positive`; `get_price_for_user` (здесь `min` с акцией; докстринг «даже если выше» устарел) / `get_regular_price_for_user`. Миграция `products/0059_*`.
- `backend/apps/products/filters.py:22,293,311` -- `visible_price_q` и `min_price`/`max_price`: перевести на цепочку. Докстринг `visible_price_q`: «специальная цена» → «цена роли», `has_special`/`no_special` → `has_role_price`/`no_role_price`.
- `backend/apps/products/serializers.py:451` -- `priced_variant_q`: добавить `vip_price`, `special_price`.
- `backend/apps/products/services/parser.py:576` -- `_map_price_type_to_field`: точные названия «VIP цены», «СПЕЦЦЕНА» сразу после `is_promo_name`.
- `backend/apps/products/services/variant_import.py:1576,1848,1901,2590` -- создание варианта, `update_variant_prices` (снятие спеццены после `price_updates`; две цены `special_price` в предложении → вид с поздним `created_at`, warning), `process_price_types` (`user_role`). `PriceType.created_at` — `models.py:964`.
- `backend/apps/products/admin.py:698,729`, `forms.py:65` -- `special_price` в `readonly_fields` (как `promo_price`), `vip_price` в полях; форма `PriceType` берёт роли из `ROLE_CHOICES`.
- `backend/apps/orders/serializers.py:245` -- `startswith("wholesale")` → дополнить `vip`, `special_price`.
- `backend/apps/banners/services.py:138`, `models.py:424` -- `vip`/`special_price` → оптовики (`startswith("wholesale")` их не ловит; неизвестная роль в `services` падает на guest).
- `backend/apps/users/admin.py:960` -- цвет роли.
- `backend/apps/products/factories.py:96,150`, `backend/tests/factories.py` -- поля.
- Без правок, подхватят цену сами: `cart/views.py:142`, `cart/models.py:154`, `orders/services/order_create.py`, `order_export.py`. Перенос гостевой корзины при входе (`cart/signals.py:85`) сохраняет гостевой снимок — как у всех ролей.
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts` (`npm run generate:types`, гейт `api-contract.yml`) -- новые значения получает enum профиля; `UserRegistrationRoleEnum` не меняется.
- `frontend/src/utils/pricing.ts:7,26,43,78`, `types/api.ts:14`, `types/index.ts:26`, `stores/authStore.ts:134`, `utils/server-auth.ts:41` -- `UserRole`, `isB2BRole`, `getPriceForRole`, `getProductDisplayPrice`, `validRoles`. Неизвестная роль в `server-auth.ts` превращается в `retail`: VIP-клиент увидит розницу при SSR. У `ProductPrice` нет полей новых ролей, и API сырые цены не отдаёт: для `vip` / `special_price` `getProductDisplayPrice` берёт `current_price` / `regular_price`.
- `frontend/src/components/business/ProductCard/ProductCard.tsx:113,158,190,198`, `product/ProductInfo.tsx:36,71,167` -- `getProductPrice` и `getPromoPricing`: правило «акция применена» через общий хелпер из `pricing.ts`; бейдж «Акция» (`ProductCard.tsx:190`, сейчас по `product.is_promo`) — по тому же правилу; списки ролей.
- `frontend/src/components/home/{Hits,NewArrivals,Promo,Sale}Section.tsx`, `app/(blue)/catalog/CatalogPageClient.tsx:482`, `home/HeroSection.tsx:97`, `ElectricHeroSection.tsx:138` -- списки ролей: добавить обе.

## Tasks & Acceptance

**Execution:**
- [x] `users/models.py` + миграция `0027`, `users/serializers.py` -- роли в `ROLE_CHOICES`, `B2B_ROLES`, `get_role_display`; исключение из саморегистрации.
- [x] `products/models.py` + миграция `0059` -- поля `vip_price`, `special_price` (null, CHECK ≥ 0), choices `PriceType`, цена по цепочке и `min` с акцией.
- [x] `pricing_policy.py`, `filters.py`, `serializers.py` -- цепочка, `INFO_PRICE_ROLES`, `priced_variant_q`; терминология «цена роли».
- [x] `parser.py`, `variant_import.py` -- распознавание по точному названию, `user_role`, снятие спеццены, две цены `special_price` в предложении.
- [x] `products/admin.py`, `users/admin.py`, `orders/serializers.py`, `banners/services.py`, `banners/models.py`, фабрики -- по Code Map.
- [x] `openapi.yaml`, `api.generated.ts` -- enum профиля.
- [x] frontend -- типы, `pricing.ts` (хелпер «акция применена»), `authStore.ts`, `server-auth.ts`, карточка и страница товара (бейдж, зачёркивание и подпись по хелперу), списки ролей.
- [x] тесты:
  - backend: `test_promo_price.py` и `test_price_logic.py` (строки «акция выше/равна цене клиента» переписать под `min`), `test_cart_order_integration.py`, `test_pricing_policy.py`, `test_product_filters.py`, `test_parser_helpers.py` (точные названия, регистр и пробелы, похожие названия), `test_price_type_role.py`, `test_user_models.py`, `tests/unit/test_serializers/test_user_serializers.py:135` (саморегистрация), тест ограничения оплаты оптовика, `test_catalog_price_visibility.py`, `banners/tests/test_services.py`; юнит-тесты `update_variant_prices` и `process_price_types` на словарях — строки матрицы про импорт. Интеграционный тест на XML не пишется: в реальных выгрузках новых видов цен нет;
  - frontend: `pricing`, `ProductCard.test.tsx`, `ProductInfo.test.tsx` (бейдж при применённой и неприменённой акции), `server-auth`.

**Acceptance Criteria:**
- Given верифицированный клиент `special_price` добавил в корзину товар со спецценой, when оформляет заказ, then `price_snapshot`, `OrderItem.unit_price` и `ЦенаЗаЕдиницу` равны `special_price`.
- Given данные импорта с видами «VIP цены» и «СПЕЦЦЕНА», when прошли `process_price_types` и `update_variant_prices`, then цены записаны в `vip_price` и `special_price`, а у `PriceType` стоят роли.
- Given соглашение контрагента с видом цен «СПЕЦЦЕНА», when импортирован контрагент, then у привязанного аккаунта роль `special_price`.
- Given акция 800 и цена клиента 700, when клиент любой роли оформляет заказ, then `OrderItem.unit_price` и `ЦенаЗаЕдиницу` равны 700.
- Given акция 800 и цена клиента 700, when клиент открывает каталог и товар, then бейджа «Акция», зачёркнутой цены и подписи «Акционная цена» нет; при цене клиента 900 — все три есть.
- Given VIP-клиент, when открывает каталог и товар (SSR и клиент), then видит цену VIP и РРЦ/МРЦ, а не розницу.
- Given `check_openapi_sync`, when запущен, then расхождений нет.

### Review Findings

Ревью 2026-10-26 (плагин Codex: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor, Graph Impact).

- [x] [Review][Patch] Карточка с неприменённой акцией считает цену сама, а не берёт `current_price` из API: тренер и представитель федерации видят розницу, опт 2–4 без своей цены — цену соседнего уровня [frontend/src/components/business/ProductCard/ProductCard.tsx:209] — medium. При `promo_price > 0` и цене клиента ниже акции `getPromoPricing` возвращает `null`, и цена идёт из `getProductPrice`. `ProductListSerializer` не отдаёт `trainer_price` / `federation_price`, поэтому тренер с ценой 700 при акции 800 и рознице 1200 видит 1200 и оплачивает 700. Для `wholesale_level3` карточка откатывается по цепочке opt3→opt2→opt1, а backend при пустом `opt3_price` берёт розницу. До правки товар с акцией всегда показывал `current_price`, так что это регрессия. Исправление: если у товара есть `promo_price > 0`, а акция не применена, брать `current_price`. Нужен тест на тренера.
- [x] [Review][Patch] Нет теста на вариант, у которого положительна только `vip_price` или `special_price` (розница 0) [backend/apps/products/serializers.py:451] — low. Если убрать новые условия из `priced_variant_q`, существующие тесты останутся зелёными. Нужен параметризованный тест по образцу `test_list_shows_variant_with_only_promo_price`: API списка и сериализация без prefetch.
- [x] [Review][Patch] SSR-тест страницы товара мокает ответ по старому правилу акции [frontend/src/app/(blue)/product/[slug]/__tests__/page.session.test.tsx:66] — low. Мок всегда отдаёт `current_price=800`, в том числе клиенту с `regular_price=700`, и требует `promo-price`. Нужно отдавать итог по сессии (700 при акции 800) и проверять сумму, отсутствие бейджа и `promo-price`.
- [x] [Review][Defer] AC6 «РРЦ/МРЦ» для VIP выполнен только по РРЦ [frontend/src/components/product/ProductInfo.tsx:185] — deferred, pre-existing: МРЦ (`msrp`) не выводят ни карточка, ни страница товара ни для одной роли; РРЦ на странице показывается только при выбранном варианте. Новые роли получили тот же набор, что и оптовики.

**Rejected:**
- false — фильтры `min_price` / `max_price` не учитывают акцию (blind): так задано в «Never» («Фильтры цены акцию не учитывают — как сейчас»).
- false — `isPromoApplied` при отсутствующем `current_price` считает акцию применённой (blind): сериализаторы варианта и списка всегда отдают `current_price` (минимум `"0.00"`), в API такого состояния не бывает. Поведение задокументировано в хелпере.
- false — `getProductDisplayPrice` для VIP берёт цену товара раньше акции варианта (blind): ветка выполняется только без `variant.current_price`, а вариант из API его всегда отдаёт.
- false — нет тестов на снятие спеццены или смену акции между корзиной и заказом (blind): снимки корзины не пересчитываются по «Never».
- rejected (правка спеки) — спеццена остаётся, когда в справочнике не осталось ни одного активного вида `special_price` (blind): такое поведение прямо задано в «Always» («Снятие спеццены»).
- rejected (правка спеки) — в «Always» буквально записано `current_price ≤ promo_price`, а код проверяет `promo_price ≤ current_price` (acceptance): код соответствует матрице I/O и AC5. Исправить нужно текст спеки — это уже отмечено в Completion Notes.
- rejected (правка спеки) — `update_variant_prices`, `process_price_types`, `_map_price_type_to_field` после правок дают `CRITICAL` / `HIGH`, а в Debug Log записан `LOW` (graph-impact): в 42 прямые зависимости входят тесты, несовместимых вызывающих слой не нашёл. Это поправка записи в спеке, а не кода.
- low — при неприменённой акции и `discount_percent > 0` в карточке появляется зачёркнутая розница (acceptance): так же выглядит товар без акции с ручным `discount_percent`, то есть оформление «как без акции». Поле ручное, на проде редкое.
- low — нет теста импорта отрицательной `vip_price` (blind): `vip_price` идёт общим путём `_map_offer_prices`, как `opt1–4`.
- low — нет сквозного теста «справочник → соглашение → роль → цена API» и SSR-теста передачи сессии для новых ролей (blind): звенья покрыты по отдельности (`test_price_type_role`, `test_customer_processor`, `server-auth.test.ts`), а сквозной тест на реальных данных пропускается без снимков.

#### Ревью 2026-10-27, второй круг

Плагин Codex: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor, Graph Impact. Graph Impact со второго запуска: в первом Git Bash в песочнице Codex упал с `CreateFileMapping ... Win32 error 5`, во втором команды шли через PowerShell. Несовместимых вызывающих и новых циклов импорта нет.

- [x] [Review][Patch] Полное сохранение варианта возвращает снятую импортом спеццену [backend/apps/products/models.py:1443] — medium. Источник: edge-case-hunter. `ProductVariant.save` через `_skip_derived_field` исключает из полного сохранения только `promo_price`. Импорт снимает `special_price` через `save(update_fields=...)` (`variant_import.py:1972`). Экземпляр, загруженный раньше (форма варианта в админке, инлайн товара), при сохранении любого другого поля, например `vip_price`, запишет в БД старую спеццену. При дельта-выгрузке предложение может больше не прийти, и клиент «Спец цена» продолжит платить снятую цену. По спеке `special_price` ведёт только импорт («как `promo_price`»), но защиты, как у `promo_price`, у неё нет. Исправление: передавать в `_skip_derived_field` несколько полей и исключать оба, плюс тест по образцу теста на `promo_price`.
- [x] [Review][Patch] Нет тестов резервного оптового баннера для `vip` и `special_price` [frontend/src/components/home/HeroSection.tsx:102] — low. Источник: verification-gap. Условия новых ролей в `HeroSection.tsx:102` и `ElectricHeroSection.tsx:139` можно удалить, и тесты останутся зелёными: `HeroSection.test.tsx:222,287` проверяет только `wholesale_level1`, а `ElectricHeroSection.test.tsx` — только гостя. Исправление: параметризовать сценарии резервного баннера (ошибка API и пустой ответ) обеими новыми ролями.
- [x] [Review][Defer] Плитка без акции показывает тренеру и представителю федерации розницу, с акцией — `current_price` из API [frontend/src/components/business/ProductCard/ProductCard.tsx:136] — deferred, pre-existing. `getProductPrice` читает `trainer_price` / `federation_price`, которых список не отдаёт. Правка прошлого круга берёт `current_price` только при `promo_price > 0`, поэтому у одного и того же клиента цена на плитке зависит от наличия акции у товара. Без акции так было и до правки. Связано с D14-2 (страница товара) и с записью про цепочку опт 2–4 в `deferred-work.md`.

**Rejected (второй круг):**
- false — фильтры `min_price` / `max_price` не учитывают акцию (blind, edge): задано в «Never», как и в первом круге.
- false — `isPromoApplied` без `current_price` считает акцию применённой (blind): API всегда отдаёт `current_price`, как и в первом круге.
- false — запасная ветка VIP в `getProductDisplayPrice` берёт цену товара раньше акции варианта (blind): ветка выполняется только без `variant.current_price`, как и в первом круге.
- false — не покрыт жизненный цикл снимка корзины после снятия спеццены (blind): по «Never» снимки корзины не пересчитываются.
- low — `parseFloat` без строгого разбора (`'800oops'`, `Infinity`) в `isPromoApplied` (blind): API отдаёт только десятичные строки DRF, на практике не встречается.
- low — нет теста выбора варианта, когда у одного варианта только `vip_price`, а у другого розница (blind): `first_variant_ordering` ставит вариант с положительной розницей первым, а порядок не менялся.
- low — гость получает `current_price=0.00`, если у всех вариантов положительна только `vip_price` / `special_price` (edge): так же работают `opt1–4` и `trainer_price` до правки; VIP-цена и розница в 1С заданы на всех товарах.
- low — нет сквозного SSR-теста сессии новых ролей и проверки `offers.price` в JSON-LD через `ProductPageClient` (blind): повтор первого круга; экран и JSON-LD берут сумму из одного `getProductDisplayPrice`, а он покрыт в `pricing.test.ts`.
- low — при неприменённой акции и `discount_percent > 0` появляется зачёркнутая розница (acceptance): повтор первого круга, оформление «как без акции».
- duplicate — AC6: МРЦ не выводится, РРЦ на странице только при выбранном варианте (blind, acceptance): уже отложено ревью 2026-10-26.
- duplicate — нет интеграционного теста импорта на реальном XML (verification-gap, disposition `defer`): уже в `deferred-work.md`, синтетические XML запрещены.
- rejected (правка спеки) — в «Always» буквально `current_price ≤ promo_price`, а код проверяет обратное (acceptance): повтор первого круга, исправлять нужно текст спеки.

#### Ревью 2026-10-27, третий круг

Плагин Codex: Blind Hunter, Edge Case Hunter, Verification Gap, Acceptance Auditor, Graph Impact (дифф `5147944e` против рабочего дерева: 60 файлов, 4000 строк, целиком). Graph Impact шёл через PowerShell в песочнице Codex: несовместимых вызывающих и новых циклов импорта нет. Все слои отработали. Новых `patch` и `decision-needed` нет.

- [x] [Review][Defer] Electric-вариант `HitsSection` показывает всем ролям сырую розницу, а не цену клиента [frontend/src/components/home/HitsSection.tsx:323] — deferred, pre-existing. Источник: verification-gap. `ElectricProductCard` получает `price={product.retail_price}`, а `ProductListSerializer.get_retail_price` отдаёт `variant.retail_price` без учёта роли. Строка стоит в `HEAD` для оптовиков, тренера и представителя федерации; спека добавила `vip` и `special_price` только в `isB2B` (показ РРЦ). VIP с ценой 900 при рознице 1200 видит на этой плитке 1200 и платит 900. Связано с записью про плитку тренера (второй круг).

**Rejected (третий круг):**
- false — фильтры `min_price` / `max_price` не учитывают акцию (blind, edge): задано в «Never» («Фильтры цены акцию не учитывают — как сейчас»), как и в первых двух кругах.
- false — `isPromoApplied` без `current_price` считает акцию применённой (blind): API всегда отдаёт `current_price`, поведение записано в докстринге хелпера (`pricing.ts:70`); повтор.
- false — запасная ветка VIP в `getProductDisplayPrice` берёт цену товара раньше акции варианта (blind): вариант с `current_price` возвращается первой строкой (`pricing.ts:129`), ветка достигается без него, а API его всегда отдаёт; повтор.
- false — нет теста снятия спеццены между корзиной и заказом (blind): снимки корзины не пересчитываются по «Never».
- false — цена клиента 800,40 при акции 800,49 показана как «800 ₽» (edge): неприменённая акция выглядит как товар без акции, а без акции цена везде идёт через `formatPrice` с округлением до рубля (`ProductInfo.tsx:174-176`); копейки показываются только в паре «акционная и зачёркнутая».
- rejected (правка спеки) — в «Always» буквально `current_price ≤ promo_price`, а код проверяет обратное (acceptance): повтор, исправлять нужно текст спеки.
- duplicate — AC6: МРЦ не выводится, РРЦ на странице только при выбранном варианте (acceptance): уже отложено ревью 2026-10-26.
- low — при неприменённой акции и `discount_percent > 0` появляется зачёркнутая розница (acceptance): повтор первого и второго кругов.
- low — `priced_variant_q` пропускает вариант, у которого положительна только скрытая `vip_price` / `special_price`, и гость увидит `current_price=0.00` (blind): тот же путь, что у `opt1–4` и `trainer_price` до спеки (`serializers.py:451`); повтор второго круга.
- low — `test_offer_outside_of_package_is_untouched` слабый (blind): `update_variant_prices` пишет спеццену только переданному варианту, массового сброса в вызывающем коде нет; пакет целиком проверяет только интеграционный тест на XML, а он запрещён «Never».
- low — нет теста с двумя соединениями PostgreSQL для `_resolve_special_price` (blind): справочник читается под `promo.lock_promo_state(shared=True)`, как у акции (`variant_import.py:1942`); дефект не показан, тест тяжёлый.
- low — админка проверена формой и прямым `save_model` без HTTP POST (blind): `save_model` — тот метод, который вызывает POST, а `TestStaleVariantSaveKeepsSpecialPrice` падал до правки.
- low — нет теста отрицательной `vip_price` при импорте (blind): `vip_price` идёт общим путём `_map_offer_prices`, как `opt1–4`; повтор первого круга.
- low — нет сквозного SSR-теста сессии новых ролей (blind): звенья покрыты по отдельности; повтор первого и второго кругов.
- low — списки ролей `isB2B` в `PromoSection` / `SaleSection` (а также `HitsSection`, `NewArrivalsSection`) не покрыты тестами новых ролей (graph-impact): все секции передают в `ProductCard` и `userRole`, и `mode`, а карточка решает по `mode === 'b2b' || isB2BRole(userRole)` (`ProductCard.tsx:540`), поэтому список на неё не влияет; он влияет только на РРЦ в Electric-ветке `HitsSection`. Тестов секций на `mode` нет и для прежних ролей, а у `PromoSection` / `SaleSection` нет даже файлов тестов.

## Implementation Notes

## Spec Change Log

- **2026-10-26, обсуждение спеки с владельцем.** Правило `min` вынесено в Intent как изменение для всех оптовых ролей. Бейдж «Акция» — только при применённой акции (раньше оставался по `is_promo`). Парсер — точные названия «VIP цены» и «СПЕЦЦЕНА» вместо подстрок. Две цены `special_price` в одном предложении — цена вида с поздним `created_at` и warning. Интеграционный тест импорта заменён юнит-тестами на словарях: реальной выгрузки с новыми видами цен нет. Терминология «специальная цена» → «цена роли» в `pricing_policy.py` и `filters.py`. Отбор раздела «Акции» по `is_promo` не меняется, записан в deferred-work.

## Review Triage Log

## Design Notes

Цепочка в `pricing_policy.py` — данные, а не ветки в `models.py` и `filters.py`:

```python
ROLE_PRICE_FIELDS["special_price"] = "special_price"
ROLE_PRICE_FALLBACKS = {"special_price": "opt1_price"}  # затем retail_price
```

Почему не алиас «VIP = опт 1»: у VIP своя цена в 1С, и менеджер может завести её отдельно от «Опт 1».

Акция, которая невыгодна клиенту (опт 1=700, акция 800), не должна выглядеть как применённая: `getPromoPricing` сейчас включает акционное оформление при любом `promo_price > 0`, поэтому нужно сравнивать `current_price` с `promo_price`. Иначе цена 700 получит подпись «Акционная цена» и жирный стиль, а `discount_percent` скроется. По тому же правилу скрывается и бейдж «Акция»: товар с акцией, которая клиенту невыгодна, не должен обещать скидку.

## Verification

**Commands:**
- `docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest <тесты из задач>` (из `docker/`) -- expected: зелёные.
- `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` перед правкой `get_regular_price_for_user`, `get_price_for_user`, `visible_price_q`, `_map_price_type_to_field`, `update_variant_prices`, `process_price_types`, `get_self_service_roles`; после — `detect-changes --scope all`, `check --cycles` (базовая линия — два цикла).
- В `frontend/`: `npm run format:check`, `npm run lint`, `npx tsc --noEmit`, `npx vitest run <тесты>` -- expected: без ошибок.
- Линтеры backend — навык `backend-lint`, после зачётного pytest, не параллельно.

## Dev Agent Record

### Implementation Plan

- Порядок: роли `users` → поля и расчёт цены `products` → цепочка в `pricing_policy.py` и фильтры → парсер и импорт 1С → админка, заказ, баннеры → контракт API → фронтенд. Тесты пишутся рядом с каждым шагом; шаги импорта и фронтенда проверены мутацией (поломка кода роняет новые тесты).
- Цепочка «поле роли → запасное поле → розница» — данные в `pricing_policy.py` (`ROLE_PRICE_FIELDS`, `ROLE_PRICE_FALLBACKS`) и две функции над ними: `role_price_fields(role)` для фильтров каталога и `resolve_role_price(variant, role)` для расчёта цены. `models.py` и `filters.py` веток по ролям не содержат.
- `min` с акцией — только в `ProductVariant.get_price_for_user`; цена роли `≤ 0` в сравнении не участвует.
- Импорт: `_map_offer_prices` пропускает виды `special_price`, выбор вида и снятие спеццены делает `_resolve_special_price` после остальных цен (по образцу `_resolve_promo_price`). Роль `PriceType.user_role` проставляет `process_price_types` по `PRICE_TYPE_ROLES`, если она пуста.
- Фронтенд: хелпер `isPromoApplied` в `pricing.ts` управляет стикером «Акция», зачёркнутой ценой и подписью «Акционная цена» в `ProductCard` и `ProductInfo`; роли `vip` / `special_price` берут цену из `current_price` / `regular_price` (`isApiPricedRole`).

### Debug Log

- GitNexus `impact` (до правок): `get_self_service_roles`, `get_regular_price_for_user`, `get_price_for_user`, `visible_price_q`, `_map_price_type_to_field`, `update_variant_prices`, `process_price_types`, `getPriceForRole`, `getProductDisplayPrice` — все `LOW`. `isB2BRole`, `getProductPrice`, `getPromoPricing` — `CRITICAL` (один прямой вызывающий — `ProductCard`, затронуты потоки `BlueHomePage`, `ElectricHomePage`, `CatalogContent`, `SearchPageClient`); ожидаемо: спека меняет карточку во всех сетках. Пользователь предупреждён до правок фронтенда.
- `detect-changes --scope all`: 50 файлов, 15 потоков, все ожидаемые (карточка товара, секции главной, баннеры, `ProductInfo`, `priced_variant_q`). `check --cycles`: только два базовых цикла.
- `check_openapi_sync` до регенерации: три расхождения (описание `ProductVariant`, enum и описание `UserProfileRoleEnum`). `spectacular --validate` переставил ключи и дал дифф на 400 строк, поэтому в `openapi.yaml` внесены только три смысловые правки (файл с CRLF); после — «Контракт синхронен». `npm run generate:types` — дифф на 6 строк.
- Падения, найденные полным прогоном: `HitsSection.test.tsx` и `NewArrivalsSection.test.tsx` ожидали стикер «Акция» у моковых товаров с `is_promo: true` без акционной цены — моки в `__mocks__/api/handlers.ts` дополнены `promo_price` / `current_price` / `regular_price` (акция применена).
- `mypy` после первого прогона: 5 ошибок в новом коде (`Any` из `getattr`, аннотации фикстур, `choices` у формы) — исправлены, итог 0 на 660 файлах.
- Тест привязки роли на реальных данных (`test_link_applies_role_from_1c.py`) в этом клоне пропускается: каталога `contragents_pricetype` нет (до правки он тоже пропускался). Критерий AC3 покрыт тестами на собранном словаре: `test_customer_processor.py` (импорт для привязанного аккаунта) и `test_link_1c_customer.py` (привязка менеджером).
- Второй круг ревью, GitNexus `impact _skip_derived_field` (до правки): `LOW`, два прямых вызывающих (`Product.save`, `ProductVariant.save`), 13 затронутых символов вместе с тестами и вызовами импорта, потоков нет. Присваиваний `.special_price =` и полных `save()` существующего варианта с этим полем в `backend/` нет: импорт пишет спеццену через `setattr` и `save(update_fields=...)`, поэтому правка его не задевает.
- Красная фаза патча 1: `test_full_save_does_not_write_special_price` и `test_admin_save_model_does_not_write_special_price` падали (`Decimal('800.00') is None`), два охранных теста (явный `update_fields` пишет `special_price`, полное сохранение пишет `vip_price`) проходили и до правки.
- Мутация патча 2: условия `vip` / `special_price` временно убраны из `HeroSection.tsx` и `ElectricHeroSection.tsx` (копии в scratchpad, после проверки восстановлены побайтно) — падают ровно 8 новых тестов, прежние зелёные. Первая попытка мутации оставила висячий `||` (синтаксическая ошибка, тесты упали бы не по делу), поэтому мутация переделана.
- Первый полный прогон vitest: красный `CatalogPage.test.tsx` («отменяет ожидающий debounce цены при сбросе фильтров», 1646 мс против 658 мс отдельно). Файл отдельно — 122 passed, повторный полный прогон — зелёный: флейк реальных таймеров под нагрузкой параллельных воркеров, к правкам не относится.
- `detect-changes --scope all`: 56 файлов, 17 потоков, все ожидаемые (карточка и `getPromoPricing`, герои главной, `ProductInfo`, `priced_variant_q`, `CatalogContent`); «critical» завышен, потому что индекс собран на `5147944`, а в дереве вся неслитая фича. `check --cycles`: только два базовых цикла.

### Completion Notes

- Выполнены все задачи и критерии приёмки. Backend: **5395 passed, 79 skipped, 0 failed** (`pytest -n 4 -m "not performance and not slow"`), `black`, `flake8`, `isort`, `mypy` чисты, `makemigrations --check` без изменений, `check_openapi_sync` без расхождений. Frontend: **4033 passed, 16 skipped**, `format:check`, `lint`, `tsc` чисты.
- **Расхождение в замороженном тексте спеки.** В «Always» («Карточка и страница товара») написано «`promo_price > 0` и `current_price ≤ promo_price`». При правиле `min` это условие верно всегда (`current_price` не бывает выше акционной), то есть акция считалась бы применённой и при цене клиента 700 против акции 800. Матрица I/O, критерий приёмки и Design Notes требуют обратного, поэтому реализовано «`promo_price > 0` и `promo_price ≤ current_price`» (клиент платит акционную цену). Текст «Always» стоит поправить.
- **Сверх Code Map, по инварианту «сырые `vip_price` / `special_price` API не отдаёт».** `OrderItemSerializer` (`depth = 1`) отдавал вложенный вариант целиком, и новые поля попали бы в ответ заказа. Они вырезаются в `to_representation` (константа `HIDDEN_ROLE_PRICE_FIELDS`), тест — `test_order_responses_do_not_expose_raw_role_prices`. Прежние сырые цены (`opt1–4`, `trainer_price`, `federation_price`) в ответе заказа остаются как были — это существующее поведение вне спеки, его стоит записать в deferred-work.
- Правило `min` меняет цену всех оптовых ролей: тесты `test_promo_price.py`, `test_price_logic.py`, `test_cart_order_integration.py` (клиент `wholesale_level3` с ценой 700 при акции 800 теперь платит 700) переписаны.
- Стикер «Акция» в карточке: `ProductBadge` сам показывает «Акция» по флагу `is_promo`, поэтому при неприменённой акции карточка передаёт ему копию товара с `is_promo: false`. Отбор раздела «Акции» и `PromoSection` не менялись.
- Список ролей `authSchemas.ts:188` (форма саморегистрации) не менялся намеренно: новые роли назначает менеджер или 1С.
- ✅ Resolved review finding [medium]: карточка с неприменённой акцией брала цену из `getProductPrice` (тренер и представитель федерации видели розницу, опт 2–4 без своей цены — соседний уровень). Теперь при `promo_price > 0` карточка берёт `current_price` из API, даже если акция не применена; `getProductPrice` не менялась. Тесты: `unapplied promo shows the API price of trainer / federation_rep` и `... of a level without its own price` (`ProductCard.test.tsx`), до правки красные.
- ✅ Resolved review finding [low]: тест `test_list_shows_variant_with_only_role_price[vip|special_price]` (`test_promo_price.py`) — API списка под пользователем роли и `ProductListSerializer` без prefetch; мутация (удаление `vip_price` / `special_price` из `priced_variant_q`) роняет оба случая.
- ✅ Resolved review finding [low]: SSR-тест `page.session.test.tsx` отдаёт итог по сессии (оптовику `current_price=700` при акции 800, гостю 800 при рознице 1200) и проверяет сумму, отсутствие стикера «Акция», подписи «Акционная цена», `promo-price` и `regular-price` у оптовика; у гостя — 800 акцией и зачёркнутую 1200.
- После правок ревью: backend **5397 passed, 79 skipped, 0 failed** (`pytest -n 4 -m "not performance and not slow"`), `black` / `flake8` / `isort` / `mypy` по изменённому файлу чисты; frontend **4036 passed, 16 skipped**, `format:check`, `lint`, `tsc` чисты; `detect-changes` — те же ожидаемые потоки, `check --cycles` — два базовых цикла.
- ✅ Resolved review finding [medium, второй круг]: полное сохранение варианта возвращало снятую импортом спеццену. `_skip_derived_field` (`products/models.py`) принимает несколько полей, `ProductVariant.save` исключает из полного сохранения `promo_price` и `special_price`; `vip_price` пишется как `opt1–4`. Тесты `TestStaleVariantSaveKeepsSpecialPrice` (`test_promo_price.py`): полное сохранение и `save_model` админки не пишут `special_price` (до правки красные), явный `update_fields` и создание пишут, `vip_price` пишется.
- ✅ Resolved review finding [low, второй круг]: нет тестов резервного оптового баннера для `vip` и `special_price`. Параметризованные сценарии (две роли × ошибка API и пустой ответ) в `HeroSection.test.tsx` и `ElectricHeroSection.test.tsx` проверяют оптовый баннер и отсутствие гостевого; мутация (удаление условий ролей) роняет все 8 новых тестов.
- После второго круга: backend **5401 passed, 79 skipped, 0 failed** (`pytest -n 4 -m "not performance and not slow"`), `black` / `flake8` / `isort` по изменённым файлам чисты, `mypy` — 0 ошибок на 660 файлах; frontend **4044 passed, 16 skipped**, `format:check`, `lint`, `tsc` чисты; `check --cycles` — два базовых цикла.
- Не сделано, нужно владельцу: добавить виды цен «VIP цены» и «СПЕЦЦЕНА» в белый список выгрузки БУС («Выгрузка информации о товарах» → «Цены»); после первой выгрузки записи `PriceType` и роли появятся сами. Миграции `users/0027` и `products/0059` применяются при деплое. Экспорт заказа в 1С не менялся: вид цен заказа для новых ролей остаётся по умолчанию («РРЦ»).

## File List

Backend:
- `backend/apps/users/models.py`, `backend/apps/users/serializers.py`, `backend/apps/users/admin.py`
- `backend/apps/users/migrations/0027_vip_special_price_roles.py` (новый)
- `backend/apps/products/models.py`, `pricing_policy.py`, `filters.py`, `serializers.py`, `admin.py`, `factories.py`
- `backend/apps/products/services/parser.py`, `backend/apps/products/services/variant_import.py`
- `backend/apps/products/migrations/0059_vip_and_special_price.py` (новый)
- `backend/apps/orders/serializers.py`
- `backend/apps/banners/models.py`, `backend/apps/banners/services.py`
- `backend/tests/factories.py`
- Тесты: `backend/apps/products/tests/test_special_price_import.py` (новый), `backend/apps/products/tests/test_promo_price.py`, `backend/apps/products/tests/unit/test_pricing_policy.py`, `test_price_logic.py`, `test_parser_helpers.py`, `backend/apps/banners/tests/test_services.py`, `backend/tests/unit/test_models/test_user_models.py`, `backend/tests/unit/test_serializers/test_user_serializers.py`, `backend/tests/unit/test_product_filters.py`, `backend/tests/unit/test_services/test_customer_processor.py`, `test_link_1c_customer.py`, `test_price_type_role.py`, `backend/tests/integration/test_cart_order_integration.py`, `test_catalog_price_filters.py`, `test_catalog_price_visibility.py`, `test_link_applies_role_from_1c.py`, `test_user_api.py`

Контракт API:
- `docs/api/openapi.yaml`, `frontend/src/types/api.generated.ts`

Frontend:
- `frontend/src/utils/pricing.ts`, `server-auth.ts`, `frontend/src/stores/authStore.ts`, `frontend/src/types/api.ts`, `types/index.ts`
- `frontend/src/components/business/ProductCard/ProductCard.tsx`, `frontend/src/components/product/ProductInfo.tsx`
- `frontend/src/components/home/HitsSection.tsx`, `NewArrivalsSection.tsx`, `PromoSection.tsx`, `SaleSection.tsx`, `HeroSection.tsx`, `ElectricHeroSection.tsx`, `frontend/src/app/(blue)/catalog/CatalogPageClient.tsx`
- `frontend/src/__mocks__/api/handlers.ts`
- Тесты: `frontend/src/utils/__tests__/pricing.test.ts`, `server-auth.test.ts` (новый), `frontend/src/app/(blue)/product/[slug]/__tests__/page.session.test.tsx`, `frontend/src/components/business/ProductCard/__tests__/ProductCard.test.tsx`, `frontend/src/components/product/__tests__/ProductInfo.test.tsx`, `frontend/src/stores/__tests__/authStore.test.ts`, `frontend/src/components/home/__tests__/HeroSection.test.tsx`, `ElectricHeroSection.test.tsx`

Спека: `_bmad-output/implementation-artifacts/spec-roles-vip-special-price.md`

## Change Log

- **2026-10-26** — Реализованы роли `vip` и `special_price` и поля `vip_price`, `special_price` с ценами из 1С; цепочка цены «поле роли → запасное поле → розница» в `pricing_policy.py`; клиент любой роли платит меньшую из цены роли и акционной; парсер опознаёт «VIP цены» и «СПЕЦЦЕНА» по точному названию, импорт ставит роли видов цен, снимает спеццену и выбирает вид при двух ценах; админка, оплата, баннеры, контракт API; фронтенд (SSR, карточка, страница товара, стикер «Акция» только при применённой акции). Статус: review.
- **2026-10-27** — Addressed code review findings - 3 items resolved (Date: 2026-10-27): карточка берёт `current_price` при неприменённой акции, тест `priced_variant_q` для `vip_price` / `special_price`, SSR-тест страницы товара по итогу сессии. Статус: review.
- **2026-10-27** — Addressed code review findings (второй круг) - 2 items resolved (Date: 2026-10-27): полное сохранение варианта не пишет `special_price` (`_skip_derived_field` принимает несколько полей, как у `promo_price`), тесты резервного оптового баннера `HeroSection` / `ElectricHeroSection` для ролей `vip` и `special_price`. Статус: review.
