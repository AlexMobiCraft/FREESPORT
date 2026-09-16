---
title: 'Маркировка рекламы на маркетинговых баннерах'
type: 'feature'
created: '2026-08-18'
status: 'done'
baseline_commit: '866cbe05442753791085f11e170ef37f15b01c0a'
review_loop_iteration: 1
context: ['{project-root}/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Маркетинговые баннеры на главной показываются без маркировки рекламы: у платформы нет ни метки «Реклама», ни способа раскрыть реквизиты рекламодателя (наименование, ИНН) и токен ERID, которых требует ФЗ «О рекламе».

**Approach:** Добавить в модель `Banner` необязательный блок рекламных реквизитов, отдавать его публичным API и показывать на маркетинговом баннере вертикальную метку «РЕКЛАМА» у правого края, раскрывающую по наведению/фокусу/клику всплывающее окно с реквизитами и кнопкой копирования ERID.

## Boundaries & Constraints

**Always:**
- Метка и окно рендерятся **только** при `is_advertisement=True` у конкретного баннера; остальные баннеры визуально не меняются.
- `is_advertisement=True` допустим **только** при `type=marketing`: на баннерах других типов метка не рисуется, поэтому молча принятый флаг означал бы рекламу без маркировки. Решение Alex, ревью 2026-08-18.
- Окно доступно не только по hover: `mouseenter`, `focus` и `click` открывают, `mouseleave`/`blur`/`Escape`/клик вне — закрывают (тач-устройства и клавиатура обязаны иметь доступ к реквизитам).
- Триггер — `<button type="button">`, размещённый **соседом** `<Link>` слайда, а не внутри него (вложенные интерактивные элементы недопустимы).
- Изменение модели строго аддитивное: существующие поля, `clean()`-правила `cta_link`, фильтрация по ролям и инвалидация кеша в `signals.py` не переписываются.
- После правки сериализатора — регенерация `docs/api/openapi.yaml` и типов фронта (гейт `api-contract.yml`).

**Ask First:**
- Любое изменение публичного контракта `/api/banners/` помимо добавления четырёх новых полей.
- Отказ от валидации ИНН или от обязательности реквизитов при `is_advertisement=True`.

**Never:**
- Не трогать `HeroSection.tsx` и electric-тему — метка только в маркетинговой карусели.
- Не вводить глобальные (общие для всех баннеров) реквизиты в конфиге/env.
- Не добавлять внешних библиотек тултипов/поповеров.
- Не блокировать переход по `cta_link`: клик по метке не должен открывать ссылку баннера.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Обычный баннер | `is_advertisement=false` | Метка «РЕКЛАМА» не рендерится | N/A |
| Рекламный баннер, наведение | `is_advertisement=true`, `advertiser_name`, `advertiser_inn`, `erid` заполнены | Окно с «Реклама», `ИНН <inn>, <name>` и кнопкой «скопировать токен» | N/A |
| ERID не заполнен | `is_advertisement=true`, `erid=""` | Окно без кнопки копирования, реквизиты показаны | N/A |
| Копирование токена | Клик по «скопировать токен» | `erid` в буфере, надпись меняется на «Скопировано» на ~2 с | При отказе Clipboard API — «Не удалось скопировать», окно остаётся открытым |
| Клавиатура | Tab на метку, затем Escape | Окно открывается по фокусу и закрывается по Escape, фокус остаётся на кнопке | N/A |
| Сохранение без реквизитов | `is_advertisement=true`, пустые `advertiser_name` или `advertiser_inn` | `ValidationError` на соответствующем поле | Форма админки показывает ошибку, объект не сохраняется |
| Некорректный ИНН | `advertiser_inn="12345"` | `ValidationError`: ИНН — 10 или 12 цифр | То же |

</frozen-after-approval>

## Code Map

- `backend/apps/banners/models.py` — модель `Banner`, `clean()` с валидацией `cta_link`; `save()` вызывает `full_clean()`, поэтому новая валидация действует и в фабриках.
- `backend/apps/banners/serializers.py` — `BannerSerializer`, явные `fields`/`read_only_fields`.
- `backend/apps/banners/admin.py` — `BannerAdmin` с fieldsets «Контент» / «Таргетинг» / «Управление».
- `backend/apps/banners/factories.py` — `BannerFactory`, `MarketingBannerFactory`.
- `backend/apps/banners/migrations/` — последняя `0006_banner_mobile_image.py`.
- `backend/apps/banners/signals.py`, `services.py` — инвалидация кеша при save/delete; новые поля попадают в кеш автоматически, правок не требуют.
- `frontend/src/types/banners.ts` — интерфейс `Banner` (ручной, не generated).
- `frontend/src/components/home/MarketingBannersSection.tsx` — `MarketingBannersCarousel`; слайд — `div.flex-[0_0_100%].min-w-0.relative`, внутри `<Link>` либо `<div>` с `<picture>`.
- `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx` — моки `bannersService`, `next/link`, `useBannerCarousel`.
- `docs/api/openapi.yaml` — схема `Banner`; сверяется CI-гейтом `.github/workflows/api-contract.yml`.
- `frontend/src/types/api.generated.ts` — генерируется из openapi.yaml, сверяется побайтово тем же гейтом.
- `frontend/src/components/home/__tests__/HeroSection.test.tsx` — 5 фикстур `Banner`; новые обязательные поля ломали `tsc`.

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/banners/models.py` — добавить поля `is_advertisement` (bool, default `False`), `advertiser_name` (CharField 255, blank), `advertiser_inn` (CharField 12, blank), `erid` (CharField 64, blank) и расширить `clean()`: при `is_advertisement=True` требовать `advertiser_name` и `advertiser_inn`, проверять ИНН на 10 или 12 цифр — чтобы маркировка не уходила в прод полупустой.
- [x] `backend/apps/banners/migrations/0007_banner_ad_disclosure.py` — миграция на четыре новых поля; все nullable/blank с дефолтами, чтобы применяться к существующим строкам без даунтайма.
- [x] `backend/apps/banners/serializers.py` — добавить четыре поля в `fields` и `read_only_fields`, чтобы фронт получал реквизиты тем же запросом.
- [x] `backend/apps/banners/admin.py` — новый fieldset «Маркировка рекламы» с четырьмя полями и пояснением; добавить `is_advertisement` в `list_filter`.
- [x] `backend/apps/banners/factories.py` — `AdvertisementBannerFactory` на базе `MarketingBannerFactory` с валидными реквизитами для тестов.
- [x] `backend/apps/banners/tests/test_models.py`, `tests/test_serializers.py` — покрыть строки матрицы «Сохранение без реквизитов», «Некорректный ИНН», «Обычный баннер» и наличие полей в ответе сериализатора.
- [x] `frontend/src/types/banners.ts` — расширить интерфейс `Banner` полями `is_advertisement: boolean`, `advertiser_name: string`, `advertiser_inn: string`, `erid: string`.
- [x] `frontend/src/components/home/AdDisclosure.tsx` — новый клиентский компонент: вертикальная метка «РЕКЛАМА» (`writing-mode: vertical-rl` + разворот текста на 180°, чтение снизу вверх) + тёмное всплывающее окно с реквизитами и копированием ERID; вся логика открытия/закрытия и clipboard внутри.
- [x] `frontend/src/components/home/MarketingBannersSection.tsx` — рендерить `<AdDisclosure>` соседом `<Link>` внутри слайда при `banner.is_advertisement`, поверх картинки (`absolute`, правый край, `z-10`).
- [x] `frontend/src/components/home/__tests__/AdDisclosure.test.tsx` — покрыть строки матрицы «Рекламный баннер», «ERID не заполнен», «Копирование токена», «Клавиатура», включая отказ Clipboard API.
- [x] `frontend/src/components/home/__tests__/MarketingBannersSection.test.tsx` — добавить кейсы: метка есть при `is_advertisement=true`, отсутствует при `false`.
- [x] `docs/api/openapi.yaml` — регенерировать через `manage.py spectacular` и обновить типы `npm run generate:types`, иначе падает гейт `api-contract.yml`.

**Acceptance Criteria:**
- Given маркетинговый баннер с `is_advertisement=true`, when пользователь наводит курсор на метку «РЕКЛАМА», then появляется окно с заголовком «Реклама» и строкой `ИНН <inn>, <advertiser_name>`.
- Given окно открыто, when пользователь кликает по метке или окну, then переход по `cta_link` баннера **не** происходит.
- Given баннеры без рекламной маркировки, when секция рендерится, then разметка и поведение карусели идентичны текущим (снапшот существующих тестов не ломается).
- Given изменён `BannerSerializer`, when запущен `python manage.py check_openapi_sync`, then расхождений нет.

## Spec Change Log

### Итерация 1 — состязательное ревью, 2026-08-18

**Пробел в замысле (разрешён человеком).** Ревьюеры независимо нашли, что флаг «Является рекламой» доступен для баннеров любого типа, а отрисовывается только в маркетинговой карусели: hero-баннер уходил бы в прод без обязательной метки. Alex выбрал запрет на уровне валидации — `clean()` отклоняет `is_advertisement=True` при `type≠marketing`. Требование внесено в замороженный раздел.

**Ошибка спеки: Design Notes про автопрокрутку.** Утверждение «карусель сама встаёт на паузу, пока открыто окно — отдельная пауза не нужна» верно только для мыши. `stopOnMouseEnter` не срабатывает на тач и с клавиатуры, а `stopOnInteraction: false` не останавливает автопрокрутку и на свайп: слайд уезжал бы через 3 секунды вместе с юридически обязательными реквизитами. Утверждение заменено, в `useBannerCarousel` добавлены `pauseAutoplay`/`resumeAutoplay`, компонент сообщает о раскрытии через `onOpenChange`.

**Ошибка спеки: требование доступности было заявлено, но не спроектировано.** Замороженный раздел требовал доступ с тач-устройств и клавиатуры, однако Design Notes не задавали механику, и реализация провалила требование по пяти осям сразу: синтезированный `mouseenter` перед `click` гасил первый тап; панель в DOM шла до триггера, из-за чего кнопка копирования была недостижима прямым Tab; `aria-label` триггера перекрывал содержимое и скринридер не зачитывал реквизиты; тап-таргет был 18px при минимуме 24px; фокус после Escape улетал на `body`. Механика зафиксирована в Design Notes.

**Известно-плохое состояние, которого удалось избежать.** Метка `text-gray-500` без подложки поверх произвольной картинки рекламодателя: различимость зависела бы от того, что загрузил менеджер, тогда как закон требует «чётко и хорошо различимо».

**KEEP — что сработало и должно пережить перевыпуск:**
- Триггер как сосед `<Link>`, а не потомок: вложенные интерактивные элементы недопустимы, и клик по метке уводил бы на `cta_link`.
- Нормализация пробелов в `clean_fields()`, а не в `clean()`: `full_clean()` вызывает их в этом порядке, и ИНН с пробелами иначе отбивается по `max_length=12` до обрезки.
- Точечная правка `docs/api/openapi.yaml` вместо полной регенерации: drf-spectacular недетерминирован в порядке ключей и даёт ~360 строк постороннего diff, а `check_openapi_sync` сверяет структуры.
- Класс `[0-9]` вместо `\d` в регулярке ИНН и отказ от переиспользования `CustomerIdentityResolver._validate_inn`: тот опирается на `str.isdigit()` с тем же Unicode-дефектом.

## Design Notes

Метка позиционируется абсолютно у правого края слайда, текст повёрнут через `writing-mode: vertical-rl` и развёрнут на 180° (`rotate-180` на самой надписи, не на кнопке — иначе уезжает скругление), поэтому читается снизу вверх; окно раскрывается влево от метки, чтобы не выходить за границу карусели:

```tsx
<div className="flex-[0_0_100%] min-w-0 relative">
  {slideContent}                         {/* <Link> или <div> с <picture> */}
  {banner.is_advertisement && (
    <AdDisclosure
      advertiserName={banner.advertiser_name}
      advertiserInn={banner.advertiser_inn}
      erid={banner.erid}
      className="absolute right-0 top-1/2 -translate-y-1/2 z-10"
    />
  )}
</div>
```

Валидация ИНН — только длина и цифры (10 для юрлиц, 12 для ИП/физлиц); контрольная сумма не проверяется: реквизиты вводит менеджер вручную, а ложное отклонение валидного ИНН дороже, чем пропуск опечатки.

Автопрокрутку приходится останавливать вручную через `pauseAutoplay()`. `stopOnMouseEnter: true` покрывает только мышь: тап и клавиатура его не запускают, а `stopOnInteraction: false` не останавливает прокрутку даже на свайп — открытое окно уезжало бы за 3 секунды.

Раскрытие устроено тремя механизмами, каждый со своей ловушкой: наведение — через `pointerenter` с проверкой `pointerType === 'mouse'` (иначе синтезированный на тапе `mouseenter` открывает окно, а следующий за ним `click` тут же закрывает); клавиатура — панель отрисована **после** триггера в DOM и спозиционирована влево через `right-full` (в обратном порядке кнопка копирования недостижима прямым Tab), Escape возвращает фокус на триггер; скринридер — реквизиты связаны с триггером через `aria-describedby`, иначе `aria-label` кнопки перекрывает содержимое и ИНН не зачитывается вовсе.

Метка получает собственную подложку и тап-таргет не меньше 24×24 CSS-px: она лежит поверх произвольной картинки рекламодателя, а закон требует пометку «чётко и хорошо различимо».

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest apps/banners/` — ожидается: все тесты баннеров зелёные.
- `cd backend && python manage.py makemigrations banners --check --dry-run` — ожидается: «No changes detected» после создания миграции.
- `cd backend && python manage.py check_openapi_sync` — ожидается: контракт синхронен.
- `cd frontend && npm run test -- MarketingBannersSection AdDisclosure` — ожидается: все тесты проходят.
- `cd frontend && npx tsc --noEmit` — ожидается: без ошибок типов.

**Manual checks (if no CLI):**
- В админке создать маркетинговый баннер с `is_advertisement=True` и реквизитами; на `/home` метка «РЕКЛАМА» видна у правого края баннера, окно раскрывается по наведению и по Tab, кнопка копирования кладёт ERID в буфер.

## Suggested Review Order

**Правила предметной области**

- Точка входа: что вообще значит «рекламный баннер» и когда флаг отвергается
  [`models.py:315`](../../backend/apps/banners/models.py#L315)

- Запрет флага вне маркетинговых баннеров — решение по пробелу в замысле
  [`models.py:334`](../../backend/apps/banners/models.py#L334)

- Класс `[0-9]` вместо Unicode-aware шортката: иначе арабо-индийские цифры проходят как ИНН
  [`models.py:31`](../../backend/apps/banners/models.py#L31)

- Нормализация до проверки полей: `full_clean` иначе рубит ИНН с пробелами по `max_length`
  [`models.py:295`](../../backend/apps/banners/models.py#L295)

- Ошибки исключённых полей уходят в NON_FIELD_ERRORS вместо ValueError в форме
  [`models.py:349`](../../backend/apps/banners/models.py#L349)

**Граница публичного API**

- Реквизиты гасятся при снятой галочке: ИНН ИП — персональные данные
  [`serializers.py:60`](../../backend/apps/banners/serializers.py#L60)

- Четыре новых поля с дефолтами — миграция применяется без даунтайма
  [`0007_banner_ad_disclosure.py:17`](../../backend/apps/banners/migrations/0007_banner_ad_disclosure.py#L17)

**Взаимодействие в UI**

- Проверка `pointerType`: без неё первый тап на мобильном открывает и тут же закрывает окно
  [`AdDisclosure.tsx:149`](../../frontend/src/components/home/AdDisclosure.tsx#L149)

- Панель после триггера в DOM — иначе кнопка копирования недостижима прямым Tab
  [`AdDisclosure.tsx:216`](../../frontend/src/components/home/AdDisclosure.tsx#L216)

- Возврат фокуса на триггер: закрытие размонтирует кнопку и фокус улетает на body
  [`AdDisclosure.tsx:85`](../../frontend/src/components/home/AdDisclosure.tsx#L85)

- `aria-describedby` — единственный способ дать скринридеру зачитать реквизиты
  [`AdDisclosure.tsx:201`](../../frontend/src/components/home/AdDisclosure.tsx#L201)

- Подложка и тап-таргет 24×24: метка лежит поверх произвольной картинки рекламодателя
  [`AdDisclosure.tsx:204`](../../frontend/src/components/home/AdDisclosure.tsx#L204)

**Связка с каруселью**

- Ручная пауза автопрокрутки: `stopOnMouseEnter` не срабатывает на тач и клавиатуру
  [`useBannerCarousel.ts:312`](../../frontend/src/hooks/useBannerCarousel.ts#L312)

- Метка — сосед `<Link>`, а не потомок: вложенные интерактивные элементы недопустимы
  [`MarketingBannersSection.tsx:216`](../../frontend/src/components/home/MarketingBannersSection.tsx#L216)

- `inert` сужен до метки: на слайд целиком он убрал бы и ссылку баннера
  [`MarketingBannersSection.tsx:147`](../../frontend/src/components/home/MarketingBannersSection.tsx#L147)

**Периферия**

- Fieldset и видимость флага в списке — рабочее место менеджера
  [`admin.py:60`](../../backend/apps/banners/admin.py#L60)

- Схема и пример ответа; пример сверяется гейтом `api-contract.yml`
  [`openapi.yaml:2079`](../../docs/api/openapi.yaml#L2079)

- Тесты доступности, тача и клавиатуры
  [`AdDisclosure.test.tsx:112`](../../frontend/src/components/home/__tests__/AdDisclosure.test.tsx#L112)

- Тесты валидации: тип баннера, не-ASCII цифры, exclude
  [`test_models.py:430`](../../backend/apps/banners/tests/test_models.py#L430)
