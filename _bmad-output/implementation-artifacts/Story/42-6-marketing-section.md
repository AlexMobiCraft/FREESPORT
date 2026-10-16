---
baseline_commit: 6b0d536f
---

# Story 42.6: Раздел маркетинга

Status: review
Baseline Revision: 6b0d536f (`develop` после мёрджа PR #315 — стори 42.5 `done`)

## Story

As a маркетолог,
I want управлять баннерами, новостями, блогом, метками товаров и витриной главной страницы,
so that я веду маркетинг сайта сам, не видя данных клиентов и служебных полей.

**Закрывает:** FR-42-18, FR-42-19, FR-42-20, FR-42-21, FR-42-22, FR-42-23. **Источник:** `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` (Story 42.6), спецификация `_bmad-output/specs/spec-staff-admin-sections/` (CAP-4, Constraints, Non-goals, Assumptions), состав раздела — `section-contents.md`, раздел «Маркетинг».

**Предусловия:**
- **Код 42.1 в `develop`** — группы ролей и наборы прав (`users/0023_staff_role_groups.py`), `/admin/` только суперпользователю. Других зависимостей у стори нет (эпик: «42.6 зависит только от 42.1»). Код 42.4/42.5 в `develop` есть и используется как образец: `ManagerAdminSite`, `admin/manager/index.html`, nginx-локация `/manager/`, smoke-скрипты `scripts/deploy/check-manager-*.sh`.
- Ветка `feature/42-6-marketing-section` от `develop`.
- **Выкат** — ручных шагов в базе нет. После выката владелец заводит учётные записи маркетологов в `/admin/` (`is_staff=True`, группа «Маркетинг»); до 42.7 руководитель этого делать не умеет.

**Чего в этой стори нет:**
- статических страниц (`Page`), списка и экспорта подписчиков, назначения скидки, правки описания товара — Non-goals спецификации и решения Alex 08.10.2026;
- записей `AuditLog` о действиях маркетолога — их нет в «Перечне действий для журнала» `section-contents.md` (Django `LogEntry` пишется штатно);
- раздела руководителя и управления сотрудниками — 42.7;
- миграций, API, OpenAPI, фронтенда Next.js. Модели меняются только поведением: `save()` у `News` и `BlogPost` (санитайзер, решение 19) и текст `Brand.clean` (решение 13).

## Утверждённые решения (не пересматривать)

1. **Раздел — отдельный сайт `/marketing/`** (SPEC, Assumptions: «Каждый раздел — отдельный вход в Django-админке (`/manager/`, `/marketing/`)»). Экземпляр `MarketingAdminSite(name="marketing")` в `freesport/admin_site.py`, заголовок «FREESPORT — Маркетинг» (UX Design Requirements эпика), `index_title = "Раздел маркетинга"`, подключение `path("marketing/", marketing_site.urls)` в `freesport/urls.py` сразу после `manager/`.
2. **В раздел пускает членство в группе «Маркетинг» или «Руководители»** при `is_active` и `is_staff`; суперпользователь — никогда, даже в группе (как решение 2 стори 42.4: у него есть `/admin/` с тем же и большим). Менеджер, сотрудник без группы, аноним — штатный 302 на `/marketing/login/`. Фильтра по региону у маркетинга нет, поэтому руководитель уже в 42.6 видит раздел целиком — это закрывает часть AC 42.7 «в разделе маркетинга ему доступно всё, что маркетологу».
3. **Общая проверка входа — базовый класс `StaffSectionAdminSite`** с атрибутом `section_groups: tuple[str, ...]`. `ManagerAdminSite` и `MarketingAdminSite` его наследуют, `has_permission` переезжает в базовый класс без изменения поведения. Кэш членства на `request` — словарь по `self.name` (`request._staff_section_access[name]`), иначе два сайта в одном процессе делили бы один атрибут. Тесты входа 42.4 (`TestEntry`, `test_manager_admin_site.py`) — без правок.
4. **Регистрация — модуль `marketing_admin.py` в каждом приложении** (`apps/banners`, `apps/common`, `apps/products`), импорт в `ready()` по образцу 42.4/42.5 (`import apps.<app>.marketing_admin  # noqa: F401 — регистрация на сайте /marketing/`). У `CommonConfig` метода `ready()` нет — добавить. Порядок безопасен, как в 42.4: `FreesportAdminConfig` стоит в `DJANGO_APPS` раньше приложений, `admin.autodiscover()` к этому моменту загрузил все `admin.py`.
5. **На сайте маркетинга зарегистрированы ровно семь моделей:** `banners.Banner`, `common.News`, `common.BlogPost`, `common.Category`, `products.Product`, `products.Brand`, `products.HomepageCategory`. `Newsletter`, `products.Category` (дерево каталога), варианты, привязки 1С, `Page`, `User`, `Order` — не регистрируются: их URL на `/marketing/` отвечают 404 штатно (`AdminSite.catch_all_view`). Страж — unit-тест состава `marketing_site._registry`.
6. **Баннеры, новости, блог — полный доступ родительскими admin-классами** (FR-42-18). Подклассы на сайте маркетинга отличаются только `view_on_site = False`. Причина: «Смотреть на сайте» ведёт через `get_absolute_url` — у новости это JSON API (`common:news-detail`), у статьи блога `reverse("blog-detail")` без пространства имён и у рубрики `common:category-detail` — `NoReverseMatch`, то есть 500 по клику. `view_on_site = False` ставится на **все** классы раздела — правило одно, без разбора по моделям.
7. **Рубрики (`common.Category`) — новый `ContentCategoryAdmin` в `apps/common/admin.py`**, зарегистрирован и на `/admin/`, и на `/marketing/` (FR-42-19: сейчас модель не зарегистрирована нигде, без `/admin/` суперпользователь тоже не смог бы вести рубрики). Колонки: название, родитель, активна, дата создания; поиск по названию; `prepopulated_fields = {"slug": ("name",)}`. **Удаление рубрики, в которой есть новости или дочерние рубрики, запрещено:** `News.category` и `Category.parent` — `on_delete=CASCADE`, и штатное удаление молча снесло бы новости вместе с рубрикой (у маркетинга есть `delete_news`, поэтому Django не остановит). `get_deleted_objects` дописывает такие новости и дочерние рубрики в `protected` — Django тогда показывает страницу «нельзя удалить» и отклоняет POST, и в карточке, и в массовом «Удалить выбранные». Статьи блога (`SET_NULL`) удалению не мешают.
8. **Товары — `MarketingProductAdmin(ProductAdmin)`, белый список** (как решение 5 стори 42.4). Наследование — ради десяти действий меток; все атрибуты отображения переопределены: `list_display`, `list_filter`, `search_fields`, `fieldsets`, `readonly_fields`, `inlines = []`, `raw_id_fields = ()`, `prepopulated_fields = {}` (иначе `AdminForm` падает с `KeyError: 'slug'` — `helpers.py:50`), `get_queryset` свой. Правятся только `is_hit`, `is_new`, `is_sale`, `is_promo`, `is_premium` — в списке (`list_editable`) и в карточке. Название, бренд, категория, `discount_percent` — только чтение (FR-42-20). `add` и `delete` — `False`.
9. **Действия меток требуют права `change`:** `permissions=["change"]` у всех десяти `@admin.action` в `ProductAdmin` (как решение 9 стори 42.4). В `/admin/` для суперпользователя ничего не меняется; в разделе маркетолог с одним `view_product` действий не видит. Действия по-прежнему пишут `queryset.update(...)` — это существующее поведение, `AuditLog` им не нужен (решение 15).
10. **Сохранение товара, бренда и категории главной — только изменённые правимые поля через `save(update_fields=[…, "updated_at"])`** (как решение 5 стори 42.5). Пустое пересечение `form.changed_data` с правимыми полями — `save()` не вызывается. Причина — импорт 1С пишет те же строки: у товара `name`, `brand`, `category`, `description`, `is_active` (`variant_import.py`), у бренда `name`, `normalized_name`, `is_active` (`variant_import.py:2343-2344`). Полный `save()` раздела вернул бы значения, прочитанные в начале запроса. Одна функция-хелпер на три admin-класса (Task 4).
11. **«Изменено» — относительно того, что сотрудник видел при открытии** (`show_hidden_initial` на правимых нефайловых полях, как `ManagerOrderForm` 42.5). Работает и в карточке, и в строках списка: форму строки `list_editable` задаёт `get_changelist_form`. Без этого Django сравнивает POST с текущей строкой БД, и сохранение списка возвращает строки, которые после открытия страницы поменял другой сотрудник или массовое действие: маркетолог открыл список (у товара X «Хит» снят), коллега поставил X «Хит», маркетолог правит товар Y и жмёт «Сохранить» — X снова без «Хита». **Отклонения устаревшей формы, как R42.5-1, нет — это осознанно:** у флажка два значения, и одновременная правка одного флажка из одного состояния даёт одно и то же; одновременная правка одного текстового или числового поля (описание бренда, порядок категории) — «последняя запись выигрывает», как во всей штатной админке. Решение Alex 16.10.2026: не критично, защиту как R42.5-1 не делать.
12. **Список товаров без цен и без N+1** (NFR-42-04). Колонки по `section-contents.md`: фото, название, бренд, категория, активен, Хит, Новинка, Распродажа, Акция, Премиум, скидка %. Родительские `rrp_display`/`msrp_display` делают запрос на строку и показывают цены — их в разделе нет. «Фото» — миниатюра первого по `pk` варианта с `main_image`, иначе первый элемент `base_images` (порядок и нормализация пути — как `ProductListSerializer.get_main_image`, `products/serializers.py:651`, но без условия цены: миниатюра нужна, чтобы узнать товар, а не повторить карточку каталога). Варианты — один `Prefetch(..., to_attr=...)` с `only("id", "product_id", "main_image")`. Фильтры: каждая метка, бренд, категория. Поиск: название и артикул. **Категория нигде не выводится через `str(category)`:** `Category.__str__` — это `full_name`, рекурсия по `parent` (`products/models.py:240-249`), каждый уровень — отдельный запрос, а `select_related("category")` цепочку родителей не подтягивает. Колонка «Категория» — display-метод `category_name` (`obj.category.name`), тот же, что в карточке. Фильтр по категории — свой `CategoryPathListFilter(admin.RelatedFieldListFilter)`: подписи вида «СПОРТ > Мячи > Футбол» строятся в памяти из одного запроса `Category.objects.only("id", "name", "parent_id")`, сортировка по подписи. Прод на 16.10.2026: 121 категория (101 активная, у 91 есть товары), глубина до 5 уровней (по уровням 1/12/41/64/3). Штатный фильтр делал бы ~300 запросов на каждое открытие списка, колонка `category` — до 4 запросов на строку, то есть ~400 на странице из 100 товаров.
13. **Бренды — `MarketingBrandAdmin(BrandAdmin)`:** правятся логотип (`image`), «Показывать на главной» (`is_featured`), описание (`description`); название и «Активный» — только чтение. Нет: `slug`, `normalized_name`, `website`, инлайна привязок 1С, колонки «Маппинги 1С» и её аннотации, действия «Объединить выбранные бренды» (`actions = []`), добавления и удаления. Импорт 1С эти три поля не пишет — конфликтов нет. **Сообщение `Brand.clean` переводится на русский:** «Для показа на главной нужен логотип» вместо «Image is required for featured brands» (`products/models.py:75`). Маркетолог — первый не-суперпользователь, который его увидит (NFR-42-03); единственный тест с прежним текстом — `apps/products/tests/test_brand_model.py:93`, его ожидание правится (отклонение от «существующие тесты без правок» — записать в Completion Notes). **Избранные бренды появляются на главной сразу после сохранения** (решение Alex 16.10.2026, вариант «а»). Главная Next объявлена с `revalidate = 3600` (`frontend/src/app/(blue)/home/page.tsx:15`) и рендерит избранные бренды на сервере. Сброс кэша API сигналом сам по себе виден на сайте только после пересборки страницы, то есть до часа спустя. Баннеры (`HeroSection` грузит их в браузере, у API нет `Cache-Control`, Redis сбрасывает сигнал), категории главной, новости и блог (`/news`, `/blog` отдаются с `no-store`) обновляются сразу — проверено на проде 16.10.2026. Механизм сброса ISR уже есть: `pages/signals.py` после commit вызывает `POST /api/revalidate` у Next в фоновом потоке, на проде `REVALIDATE_SECRET` задан, `FRONTEND_INTERNAL_URL=http://frontend:3000`.
    - **Сброс — общий сервис `apps/common/services/nextjs_revalidate.py`:** функция `_revalidate_nextjs` переезжает из `pages/signals.py` как `revalidate_nextjs_path(path)` без изменения логики и текстов логов, рядом — `revalidate_nextjs_path_in_background(path)` (daemon-поток, как сейчас в `pages`). `pages/signals.py` зовёт фоновую функцию.
    - **Сигнал брендов (`products/signals.py`)** там же, где сбрасывает `FEATURED_BRANDS_CACHE_KEY`, в том же `on_commit` запускает сброс `/home`, но **только если бренд был или стал избранным** (`old["is_featured"] or instance.is_featured`; при создании и удалении — `instance.is_featured`). Неизбранный бренд на главной не виден, а импорт 1С правит `name`/`is_active` у многих брендов: без условия каждый прогон слал бы запрос в Next на каждый такой бренд.
    - **Отказ сброса не ломает сохранение:** ошибки и 401 пишутся `warning` в лог (как сейчас у страниц), бренд в худшем случае появится через час, как до стори. Подсказки в форме нет.
    - **Механизм на проде ни разу не наблюдался в работе:** за 30 дней в логах backend 0 строк `Next.js revalidation triggered`. Поэтому в выкат добавлена проверка по логу (шаг выката 5).
    - **Тесты сброса переезжают вместе с функцией:** `RevalidateNextjsTest` из `apps/pages/tests.py` (патчит `apps.pages.signals.requests.post`, логгер `apps.pages.signals`) переносится в `tests/unit/test_nextjs_revalidate.py` с новым путём патча и логгером, проверки и ожидания прежние. Это второе разрешённое отклонение от «существующие тесты без правок» — записать в Completion Notes.
14. **Категории на главной — `MarketingHomepageCategoryAdmin(HomepageCategoryAdmin)`:** правятся `icon`, `image`, `sort_order`; название, родитель и «Активная» — только чтение; добавления и удаления нет (как у родителя). **`icon` добавлен к «картинке» `section-contents.md`:** главная показывает `category.icon || category.image` (`frontend/src/components/home/CategoriesSection.tsx:80-81`), и без иконки правка картинки у категории с иконкой не видна на сайте. **Выборка — корни витрины:** прямые дети корневого якоря `ROOT_CATEGORY_NAME` — тот же круг, что `homepage_categories_q()` (`products/filters.py:486`), но без условия `sort_order > 0`, чтобы категорию можно было и убрать с главной (порядок 0), и вернуть. Подкатегории на главную не выводятся, их в разделе нет. `list_filter = ("is_active",)` (фильтр по родителю при одной ветке бессмыслен). **`is_active` — только чтение (решение Alex 16.10.2026: маркетолог меняет только категории на главной).** `HomepageCategory` — proxy `products.Category`, поэтому `is_active` здесь — активность категории каталога целиком: снятие убрало бы категорию со всего сайта. Убрать категорию с главной можно порядком 0. `list_editable = ("sort_order",)` — родительский `("sort_order", "is_active")` переопределяется; в карточке `is_active` в `readonly_fields`. Эпик (FR-42-22) и `section-contents.md` поправлены. **`parent` в `readonly_fields` — осознанное исключение из урока «readonly-FK только display-методом» (решение 12 стори 42.4).** Django рисует readonly-FK ссылкой на карточку на текущем сайте, но `products.Category` на `/marketing/` не зарегистрирована: `reverse` получает `NoReverseMatch`, `AdminReadonlyField` его перехватывает и выводит текст. Исключение держится на том, что модель не зарегистрирована. Если 42.7 или позже зарегистрирует `products.Category` на этом сайте, поле нужно заменить display-методом; AC12 это поймает. `get_queryset` берёт `select_related("parent")`, иначе колонка «Родитель» в списке делает запрос на строку.
15. **Журнала `AuditLog` у раздела нет.** «Перечень действий для журнала» (`section-contents.md`) действий маркетинга не содержит, 42.9 строит ленту по действиям трёх ролей из этого перечня. Django `LogEntry` пишется штатно.
16. **Главная — `admin/marketing/index.html`** по образцу `admin/manager/index.html`: пустой `{% block sidebar %}` (блок «Последние действия» строит ссылки `LogEntry.get_admin_url()` в закрытую `/admin/`, решение 13 стори 42.4), над списком моделей — плашка «Подписчиков: N (+M за 30 дней)». Блоки переименовывает `get_app_list`: приложение `common` («Общие утилиты») → «Новости и блог», модель `common.Category` («Категории») → «Рубрики» — иначе рядом с «Категориями для главной» две похожие «Категории».
17. **Подписчики — `newsletter_stats()` в `apps/common/marketing_admin.py`**, зовёт `MarketingAdminSite.index` с импортом внутри метода (как `manager_queue`, решение 11 стори 42.5: модуль раздела сам импортирует `marketing_site`). Один агрегирующий запрос: `Newsletter.objects.filter(is_active=True).aggregate(total=Count("pk"), recent=Count("pk", filter=Q(subscribed_at__gte=now - 30 дней)))`. «+M» — активные подписки с датой подписки за последние 30 дней. Повторная подписка после отписки сохраняет исходную `subscribed_at` (`common/services/newsletter_subscription.py:73`) и в прирост не попадает — ограничение данных, не дефект стори. Плашку видит каждый, кого пускает раздел: `Newsletter` на сайте не зарегистрирован, проверять модельные права не по чему.
18. **Nginx проксирует `/marketing/` в Django** — локации в `docker/nginx/conf.d/default.conf` и `local.conf` копией `/manager/` (урок 42.4, решение 11: без локации путь уходит в Next `(blue)/[slug]` и отвечает 404). **Smoke-проверки маршрута параметризуются разделом:** `check-manager-route.sh` и `release-has-manager-route.sh` принимают необязательный второй аргумент — имя раздела, по умолчанию `manager` (имена файлов не меняются: на них ссылаются `main.yml`, `deploy.yml` и тесты). `main.yml` и `deploy.yml` проверяют `/marketing/` анонимно тем же скриптом. Проверка входа с cookie (`check-manager-session.sh`) для маркетинга не нужна: локация — байт в байт копия `/manager/`, а передачу cookie через неё уже проверяет вход менеджера на тех же конфигах.
19. **HTML новостей и блога очищается на бэкенде при сохранении** (решение Alex 16.10.2026). Фронтенд выводит `content` без очистки: `dangerouslySetInnerHTML={{ __html: news.content || news.excerpt }}` (`frontend/src/app/(blue)/news/[slug]/page.tsx:121`, `blog/[slug]/page.tsx:130`). До этой стори HTML писал только суперпользователь, 42.6 впервые даёт запись роли ниже владельца. Путь атаки: `<script>` в новости на `optisport.ru` работает на том же origin, что `/admin/`; при визите суперпользователя скрипт читает `csrfmiddlewaretoken` со страницы `/admin/users/user/add/` и отправляет POST с новым суперпользователем — эскалация «маркетинг → владелец». CSP защиты не даёт (tech-debt п.23).
    - **Общий хелпер `sanitize_rich_html()` в `apps/common/utils/html_sanitizer.py`.** В него переносятся без изменений `_STRIP_BLOCKS_RE` (блоки `<style>`/`<script>`/`<head>` удаляются вместе с содержимым до bleach, иначе CSS остаётся текстом), белый список тегов и атрибутов, `protocols=["http", "https", "mailto"]` и `strip=True` из `Page.save` (`apps/pages/models.py:16`, `:61-155`). `Page.save` вызывает хелпер со своим списком: поведение страниц прежнее, `tests/integration/test_pages_api.py` проходит без правок. `bleach==6.2.0` уже есть в `requirements.txt`, новой зависимости нет.
    - **Для новостей и блога белый список — страничный без `meta` и `link`.** `<meta http-equiv="refresh">` в теле новости уводит посетителя на чужой сайт, `<link rel="stylesheet">` подгружает чужой CSS. Страницам `Page` эти теги нужны для полных HTML-документов, поэтому их список не меняется: `Page` маркетингу не выдаётся (Non-goals).
    - **`News.save()` и `BlogPost.save()` очищают `content` и `excerpt`.** `excerpt` — запасной `content` на странице статьи. Очистка в `save()`, а не в форме: она закрывает любой путь записи, и `/marketing/`, и `/admin/`.
    - **Существующие записи не переписываются, миграции нет.** На проде 16.10.2026 3 новости и 3 статьи, все от владельца; очистятся при следующем сохранении. Три из шести — полные HTML-документы с `<html>/<head>/<style>`. Первое сохранение удалит их `<style>`, и внешний вид этих записей может измениться. После выката владелец проверяет их глазами (шаг выката 4).

## Acceptance Criteria

### AC1 — вход в раздел

**Given** маркетолог, руководитель, менеджер, сотрудник без группы, заблокированный маркетолог, маркетолог без `is_staff`, суперпользователь, суперпользователь в группе «Маркетинг» и аноним
**When** каждый открывает `/marketing/` и `/marketing/products/product/`
**Then** маркетолог и руководитель получают 200, в HTML — «FREESPORT — Маркетинг»
**And** остальные получают 302 на `/marketing/login/`
**And** вход в `/manager/` и `/admin/` для всех ролей прежний (тесты 42.1 и 42.4 без правок)

### AC2 — контент: рубрика, новость, статья, баннер

**Given** маркетолог
**When** он создаёт через `/marketing/` рубрику, затем новость и статью блога в этой рубрике (опубликованы, дата публикации в прошлом), затем маркетинговый баннер со сроком показа, действующим сейчас
**Then** все четыре сохранены, новость и статья отдаются публичным API (`/api/v1/news/`, `/api/v1/blog/`) с этой рубрикой, баннер — `/api/v1/banners/?type=marketing`
**And** новость с датой публикации в будущем, неопубликованная статья и баннер с истёкшим сроком в API не попадают
**And** у рубрики, новости и статьи в карточке нет ссылки «Смотреть на сайте»

### AC3 — удаление рубрики

**Given** рубрика с новостью, рубрика с дочерней рубрикой, рубрика только со статьёй блога и пустая рубрика
**When** маркетолог удаляет каждую из карточки и массовым «Удалить выбранные»
**Then** первые две не удаляются (страница «нельзя удалить», POST отклонён), новость и дочерняя рубрика на месте
**And** рубрика со статьёй удаляется, статья остаётся без рубрики; пустая удаляется
**And** суперпользователь видит рубрики в `/admin/common/category/`

### AC4 — список товаров

**Given** маркетолог открывает `/marketing/products/product/`
**When** страница отрисована
**Then** колонки: фото, название, бренд, категория, активен, Хит, Новинка, Распродажа, Акция, Премиум, скидка %; фильтры — пять меток, бренд, категория
**And** пять меток — флажки в строках (`form-N-is_hit` … `form-N-is_premium`), `discount_percent` — только текст
**And** подписи фильтра «Категория» — полный путь («СПОРТ > Мячи > …»), колонка «Категория» — только название
**And** в выпадающем списке действий ровно десять действий меток, без «Удалить выбранные» и без действий со скидкой
**When** он ставит «Хит» товару A в списке и сохраняет, затем выбирает товары B и C и применяет «Снять отметку новинка»
**Then** у A `is_hit=True`, у B и C `is_new=False`, остальные поля и товары не изменились
**And** в HTML списка нет РРЦ, МРЦ, цен, остатков, `onec_id`, НДС

### AC5 — карточка товара

**Given** маркетолог открывает карточку товара
**When** страница отрисована
**Then** в форме правятся ровно пять меток
**And** название, бренд (ссылка на `/marketing/products/brand/<id>/change/`), категория (текст без ссылки) и скидка — только чтение
**And** в HTML нет ни поля (`name="…"`), ни подписи: блок 1С (`onec_id`, `parent_onec_id`, `onec_brand_id`, `sync_status`, `last_sync_at`, `error_message`, `onec_deleted`), НДС (`vat_rate`), `slug`, `specifications`, `description`, `short_description`, `base_images`, `seo_title`, `seo_description`, `is_featured`, `min_order_quantity`; нет формсетов вариантов и изображений; нет цен и остатков
**And** кнопок «Добавить» и «Удалить» нет
**When** он отправляет карточку с изменённым «Хитом» и подделанными `name`, `description`, `slug`, `vat_rate`, `onec_id`, `discount_percent`, `brand`, `category`, `is_active`, `specifications`
**Then** изменён только `is_hit`, остальные поля прежние

### AC6 — сохраняются только изменённые поля

**Given** маркетолог открыл карточку товара
**When** импорт 1С в это время меняет `name` и `description` товара, а маркетолог сохраняет карточку с новой меткой
**Then** `Product.save` вызван с `update_fields` из этой метки и `updated_at`, новые `name` и `description` импорта сохранились
**And** карточка без изменений не вызывает `save()` и не меняет `updated_at`
**Given** маркетолог открыл список товаров (у X «Хит» снят), коллега после этого поставил X «Хит» из своей карточки
**When** маркетолог меняет в списке только метку товара Y и сохраняет
**Then** у Y метка изменена, у X «Хит» остался поставленным
**And** то же для бренда (`is_featured` из другой карточки не сбрасывается правкой описания) и для категории главной (`sort_order` строки X не возвращается сохранением списка с правкой строки Y)

### AC7 — бренды

**Given** маркетолог открывает бренд
**When** он ставит «Показывать на главной» и загружает логотип
**Then** изменения сохранены, `/api/v1/brands/featured/` отдаёт бренд после сохранения (кэш `FEATURED_BRANDS_CACHE_KEY` сбрасывает сигнал `products/signals.py`)
**And** «Показывать на главной» без логотипа — ошибка формы «Для показа на главной нужен логотип»
**And** после commit сохранения бренда, который был или стал избранным, вызывается сброс ISR пути `/home` (`revalidate_nextjs_path_in_background("/home")`); правка неизбранного бренда, в том числе импортом 1С, сброс не вызывает; удаление избранного бренда — вызывает
**And** отказ Next (исключение, HTTP 401) не мешает сохранению бренда и пишется `warning` в лог
**And** в карточке правятся только логотип, флаг и описание; название и «Активный» — только чтение; `slug`, `normalized_name`, `website` отсутствуют
**And** нет инлайна привязок 1С (формсета `onec_mappings`), колонки «Маппинги 1С», действия «Объединить выбранные бренды», кнопок «Добавить» и «Удалить»

### AC8 — категории на главной

**Given** корни витрины (дети якоря «СПОРТ»), подкатегория и категория вне якоря
**When** маркетолог открывает `/marketing/products/homepagecategory/`
**Then** в списке только корни витрины; `sort_order` — поле в строках, `is_active` — только значок (нет `form-N-is_active`)
**When** он меняет порядок категории в списке, а в карточке — иконку и картинку
**Then** изменения сохранены; название, родитель и «Активная» — только чтение (в HTML карточки нет `name="is_active"`)
**And** подделанный POST карточки и списка с `is_active=False` активность категории не меняет
**And** порядок 0 убирает категорию из ответа `/api/v1/categories/?is_homepage=true`, порядок больше нуля возвращает
**And** карточка подкатегории и категории вне якоря по прямому URL — 404 (вне выборки раздела)

### AC9 — главная с подписчиками

**Given** 120 активных подписчиков, из них 15 подписались за последние 30 дней, и 7 отписавшихся (из них 2 — за последние 30 дней)
**When** маркетолог или руководитель открывает `/marketing/`
**Then** видно «Подписчиков: 120 (+15 за 30 дней)»
**And** без подписчиков — «Подписчиков: 0 (+0 за 30 дней)»
**And** подписка ровно 30 дней назад плюс минута не входит в прирост, минус минута — входит
**And** блоки главной: «Баннеры», «Новости и блог» (с моделью «Рубрики»), «Товары»; блока «Последние действия» нет

### AC10 — отказ по прямым URL

**Given** маркетолог
**When** он открывает по прямому URL клиентов, заказы и статические страницы в `/manager/` и `/admin/`, раздел менеджера `/manager/`, список подписчиков (`/admin/common/newsletter/`) и те же модели под `/marketing/` (`users/user/`, `orders/order/`, `pages/page/`, `common/newsletter/`), а также служебные модели под `/marketing/` (`products/category/`, `products/productvariant/`, `products/brand1cmapping/`, `common/auditlog/`)
**Then** `/manager/…` и `/admin/…` отвечают 302 на страницу входа своего сайта, `/marketing/…` — 404
**And** `add` товара, бренда и категории главной и `delete` любого из них отвечают 403
**And** раздел руководителя появится в 42.7 — его отказ проверяет 42.7

### AC11 — права внутри раздела

**Given** член «Маркетинг», у группы которого в тесте оставлены только `view_*` права раздела
**When** он открывает список и карточку товара, бренда, категории главной, отправляет POST карточки, сохранение списка (`_save`) и действие метки
**Then** карточки только для чтения (в форме нет полей ввода), в списках нет флажков меток и полей порядка
**And** POST карточки и сохранения списка отвечают 403, действий меток в списке нет, подделанный POST действия ничего не меняет
**And** блоки моделей, на которые у группы нет `view`, на главной не показаны (штатный `get_app_list`)

### AC12 — ссылки раздела ведут в раздел

**Given** маркетолог на главной, в списках и карточках всех семи моделей и в истории товара
**When** страница отрисована, в том числе после сохранения товара (есть `LogEntry`)
**Then** в HTML нет `href="/admin/` и нет `view_on_site`-ссылки
**And** редирект после «Сохранить» ведёт на список раздела, после «Сохранить и продолжить» — на карточку раздела
**And** кнопка «+» у поля рубрики в карточке новости ведёт на `/marketing/common/category/add/`

### AC13 — число запросов (NFR-42-04)

**Given** 5 товаров с вариантами и фото, затем 50
**When** маркетолог открывает список товаров
**Then** число SQL-запросов в обоих случаях одинаковое
**And** товары в категориях четвёртого уровня (как на проде), и число запросов не растёт с числом категорий в фильтре (5 и 50 категорий глубиной 4)
**And** то же для списка брендов (5 и 50), списка категорий главной (3 и 12 корней витрины) и для главной (3 и 30 подписчиков)

### AC14 — маршрут через nginx

**Given** `default.conf` и `local.conf`
**When** проверяются статическим тестом и smoke-скриптом
**Then** локация `/marketing/` есть в обоих, проксирует в `http://backend` и подключает сниппет заголовков
**And** `check-manager-route.sh <url> marketing` требует 302 ровно на `/marketing/login/?next=/marketing/` и страницу входа Django; без второго аргумента скрипт проверяет `/manager/`, как раньше
**And** `release-has-manager-route.sh <коммит> marketing` отличает релиз с разделом от релиза до 42.6; без второго аргумента — прежнее поведение
**And** `main.yml` проверяет `/marketing/` на обоих конфигах, `deploy.yml` — на проде у релиза с разделом

### AC15 — регрессия и проверки

**Given** итоговая ветка
**When** в Docker выполняются полный backend-прогон, `black --check`, `isort --check-only`, `flake8`, `mypy`, `makemigrations --check`
**Then** всё зелёное; ожидания существующих тестов не меняются, кроме строки `test_brand_model.py:93` и переноса `RevalidateNextjsTest` в `tests/unit/test_nextjs_revalidate.py` с прежними проверками (решение 13)

### AC16 — очистка HTML новостей и блога

**Given** маркетолог
**When** он сохраняет через `/marketing/` новость и статью, у которых в `content` и `excerpt` есть `<script>alert(1)</script>`, `<img src="x" onerror="…">`, `<a href="javascript:…">`, `<iframe>`, `<style>body{display:none}</style>`, `<meta http-equiv="refresh" content="0;url=https://evil.example">`, `<link rel="stylesheet" href="…">`, а рядом разрешённые `<h2>`, `<p class="lead">`, `<ul><li>`, `<strong>`, `<a href="https://…">`
**Then** в БД и в ответах детальных эндпоинтов новостей и блога нет `<script`, `onerror`, `javascript:`, `<iframe`, `<style`, текста `body{display:none}`, `<meta`, `<link`
**And** разрешённая разметка и текст на месте
**And** то же при сохранении суперпользователем в `/admin/`
**And** `Page` очищается как раньше: `<meta>` и `<link>` в её списке остаются, `tests/integration/test_pages_api.py` без правок

## Tasks / Subtasks

- [x] **Task 0 — GitNexus pre-flight** (AGENTS.md)
  - [x] `npx gitnexus status`. При `stale` — `git diff --stat <indexed> HEAD -- backend/apps backend/freesport`: пусто — переиндексация не нужна, иначе попросить Alex выполнить `! npx gitnexus analyze --skip-agents-md`. При подготовке стори индекс свежий на `6b0d536`.
  - [x] `npx gitnexus impact <symbol> --direction upstream -r "C:\Users\1\DEV\FREESPORT"` по `ManagerAdminSite`, `ProductAdmin`, `BrandAdmin`, `HomepageCategoryAdmin`, `BannerAdmin`, `NewsAdmin`, `BlogPostAdmin`, `CommonConfig`; `Brand.clean` — через `cypher` по `products/models.py` (имя `clean` неоднозначно). При подготовке: `ManagerAdminSite` — LOW, 3 прямых импорта (`freesport/urls.py`, `apps/users/manager_admin.py`, `apps/orders/manager_admin.py`); остальные — LOW, 0–1 прямых (`NewsAdmin`/`BlogPostAdmin` — связь импорта модуля из `urls.py`). Сообщить Alex blast radius до правок.

- [x] **Task 1 — сайт `/marketing/`** (AC1, AC9, AC12; решения 1–3, 16, 17)
  - [x] `freesport/admin_site.py`: базовый класс `StaffSectionAdminSite(admin.AdminSite)` с `section_groups: tuple[str, ...] = ()` и `has_permission`: `user.is_active and user.is_staff`, не `is_superuser`, членство в `section_groups` — один запрос на запрос и сайт, кэш `request._staff_section_access: dict[str, bool]` по `self.name` (решение 3). `ManagerAdminSite(StaffSectionAdminSite)` с `section_groups = (MANAGERS_GROUP, SUPERVISORS_GROUP)` — свой `has_permission` удалить, остальное (`index`, `get_app_list`, заголовки, docstring) не менять. Docstring модуля: + раздел маркетинга.
  - [x] `MarketingAdminSite(StaffSectionAdminSite)`: `section_groups = (MARKETING_GROUP, SUPERVISORS_GROUP)`, `site_header = site_title = "FREESPORT — Маркетинг"`, `index_title = "Раздел маркетинга"`, `index_template = "admin/marketing/index.html"`; `index` — `from apps.common.marketing_admin import newsletter_stats` внутри метода, `extra_context = {**(extra_context or {}), "newsletter_stats": newsletter_stats()}`; `get_app_list` — переименования решения 16 (`app_label == "common"` → «Новости и блог»; модель `object_name == "Category"` в этом приложении → «Рубрики»). `marketing_site = MarketingAdminSite(name="marketing")`.
  - [x] `freesport/urls.py`: `from freesport.admin_site import manager_site, marketing_site`, `path("marketing/", marketing_site.urls)` после `manager/` с комментарием «Раздел маркетинга (стори 42.6)». Маркер для `release-has-manager-route.sh` — ровно `path("marketing/", marketing_site.urls)` (Task 5).
  - [x] `backend/templates/admin/marketing/index.html`: `{% extends "admin/index.html" %}`, комментарий шаблона (42.6, почему пустой sidebar), `{% block content %}` — `<div class="module" id="marketing-subscribers">` с текстом из `newsletter_stats` и затем `{{ block.super }}`; `{% block sidebar %}{% endblock %}`.

- [x] **Task 2 — новости, блог, рубрики, подписчики** (AC2, AC3, AC9, AC12; решения 5–7, 17)
  - [x] `apps/common/admin.py`: `ContentCategoryAdmin` (решение 7), `@admin.register(Category)` — импорт `Category` в список моделей модуля. `view_on_site = False`. `get_deleted_objects(self, objs, request)`: `deleted, model_count, perms_needed, protected = super()…`; `protected` дополнить строками «Новость: <заголовок>» по `News.objects.filter(category__in=objs)` и «Рубрика: <название>» по `Category.objects.filter(parent__in=objs).exclude(pk__in=[o.pk for o in objs])` (дочерняя рубрика, удаляемая вместе с родителем в том же выборе, всё равно сносит свои новости каскадом — её новости попадут в `protected` своей строкой, поэтому исключение безопасно; проверить тестом выбора «родитель + ребёнок с новостью»). Вернуть кортеж с дополненным `protected`.
  - [x] Новый модуль `apps/common/marketing_admin.py`: docstring; `MarketingNewsAdmin(NewsAdmin)`, `MarketingBlogPostAdmin(BlogPostAdmin)` — только `view_on_site = False`; регистрация `marketing_site.register(News, …)`, `(BlogPost, …)`, `(Category, ContentCategoryAdmin)`; функция `newsletter_stats() -> dict[str, Any]` — решение 17, возвращает `{"total": …, "recent": …, "text": f"Подписчиков: {total} (+{recent} за 30 дней)"}`; граница — `subscribed_at__gte=timezone.now() - timedelta(days=30)`.
  - [x] `apps/common/apps.py`: `CommonConfig.ready()` с импортом `apps.common.marketing_admin`. Проверить, что модуль `apps.common` не делает тяжёлых импортов на уровне модуля, ломающих порядок (`common/admin.py` импортирует `CustomerSyncMonitor` — к `ready()` это уже загружено autodiscover'ом).

- [x] **Task 3 — баннеры** (AC2, AC12; решения 5, 6)
  - [x] Новый модуль `apps/banners/marketing_admin.py`: `MarketingBannerAdmin(BannerAdmin)` с `view_on_site = False`, `marketing_site.register(Banner, MarketingBannerAdmin)`. Импорт в `BannersConfig.ready()` рядом с `signals`.

- [x] **Task 4 — товары, бренды, категории главной** (AC4–AC8, AC11–AC13; решения 8–14)
  - [x] `apps/products/admin.py`: `permissions=["change"]` во всех десяти `@admin.action(...)` `ProductAdmin` (решение 9). Больше `ProductAdmin` не трогать.
  - [x] `apps/products/models.py:75`: текст ошибки `Brand.clean` — «Для показа на главной нужен логотип»; `apps/products/tests/test_brand_model.py:93` — ожидание по новому тексту (решение 13).
  - [x] Новый модуль `apps/products/marketing_admin.py`:
    - `class SeenValuesForm(forms.ModelForm)` (решение 11): атрибут класса `seen_fields: tuple[str, ...] = ()`; в `__init__` — `show_hidden_initial = True` для каждого имени из `seen_fields`, которое есть в `self.fields`. Docstring: зачем (сохранение списка не возвращает чужие правки) и почему без отклонения устаревшей формы (решение 11).
    - Хелпер сохранения (решение 10), например `save_changed_fields(obj, form, editable: tuple[str, ...]) -> None`: `changed = [n for n in editable if n in form.changed_data]`; пусто — `return`; иначе `obj.save(update_fields=[*changed, "updated_at"])`. Каждый из трёх admin-классов зовёт его из `save_model` (её же зовёт сохранение `list_editable`, `options.py` `changelist_view`). Файловые поля (`image`, `icon`) — в `editable`, но не в `seen_fields`: `FileField.has_changed` и так истинно только при загрузке или очистке, а `FileField.pre_save` в `update_fields` сохраняет файл в хранилище.
    - `MarketingProductAdmin(ProductAdmin)` (решения 8, 12): `LABEL_FIELDS = ("is_hit", "is_new", "is_sale", "is_promo", "is_premium")`; `form` — `SeenValuesForm`-подкласс с `seen_fields = LABEL_FIELDS`; `get_changelist_form(self, request, **kwargs)` → `super().get_changelist_form(request, form=<тот же класс>, **kwargs)`; `list_display = ("photo", "name", "brand", "category_name", "is_active", *LABEL_FIELDS, "discount_percent")` (не `"category"`, решение 12), `list_display_links = ("name",)`, `list_editable = LABEL_FIELDS`; `list_filter = (*LABEL_FIELDS, "brand", ("category", CategoryPathListFilter))`; `search_fields = ("name", "article")`; `fieldsets = (("Товар", {"fields": ("name", "brand_link", "category_name", "discount_percent")}), ("Метки", {"fields": LABEL_FIELDS}))`; `readonly_fields = ("name", "brand_link", "category_name", "discount_percent")`; `get_fieldsets`/`get_readonly_fields` возвращают атрибуты как есть (как 42.5); `inlines = []`, `raw_id_fields = ()`, `prepopulated_fields = {}`, `view_on_site = False`; `has_add_permission`/`has_delete_permission` → `False`; `get_queryset` — `Product.objects.select_related("brand", "category").prefetch_related(Prefetch("variants", queryset=ProductVariant.objects.exclude(main_image="").exclude(main_image__isnull=True).only("id", "product_id", "main_image").order_by("pk"), to_attr="marketing_photo_variants"))` (родительский `prefetch_related("variants")` не нужен — `rrp_display` в разделе нет; проверить, что `ModelAdmin.get_queryset` с `get_ordering` применён: начать с `super(ProductAdmin, self).get_queryset(request)`); `save_model` → хелпер с `LABEL_FIELDS`; `actions` — унаследованные десять.
    - `class CategoryPathListFilter(admin.RelatedFieldListFilter)` (решение 12): переопределить `field_choices(self, field, request, model_admin)` — один запрос `Category.objects.only("id", "name", "parent_id")`, словарь по `id`, путь «Корень > … > Лист» обходом `parent_id` в памяти (с защитой от цикла: посещённые `id`), список `(pk, путь)` по возрастанию пути. Docstring: почему не штатный (`__str__` → `full_name` → запрос на уровень, цифры с прода).
    - display-методы: `photo` («Фото») — `<img>` по решению 12 через `format_html`, без фото — «—»; `brand_link` («Бренд») — ссылка `reverse(f"{self.admin_site.name}:products_brand_change", args=[obj.brand_id])`; `category_name` («Категория») — `obj.category.name` текстом (дерево каталога в раздел не входит; урок 42.4, решение 12 — readonly-FK в карточке раздела только display-методом).
    - `MarketingBrandAdmin(BrandAdmin)` (решение 13): `BRAND_FIELDS = ("image", "is_featured", "description")`; форма — `SeenValuesForm`-подкласс с `seen_fields = ("is_featured", "description")`; `list_display = ("image_preview", "name", "is_featured", "is_active")`; `list_filter = ("is_featured", "is_active")`; `search_fields = ("name",)`; `fieldsets = ((None, {"fields": ("name", "is_active", "image", "is_featured", "description")}),)`; `readonly_fields = ("name", "is_active")`; `prepopulated_fields = {}`, `inlines = []`, `actions: list = []`, `view_on_site = False`; `get_queryset` — `super(BrandAdmin, self).get_queryset(request)` (без аннотации привязок); `has_add_permission`/`has_delete_permission` → `False`; `save_model` → хелпер с `BRAND_FIELDS`. `Brand.save()` пересчитывает `normalized_name` всегда — при `update_fields` без него это ничего не пишет, это ожидаемо. Сигналы кэша брендов (`products/signals.py`) срабатывают и на `save(update_fields=…)`.
    - `MarketingHomepageCategoryAdmin(HomepageCategoryAdmin)` (решение 14): `CATEGORY_FIELDS = ("icon", "image", "sort_order")`; форма и форма строки списка — `SeenValuesForm`-подкласс с `seen_fields = ("sort_order",)` (через `form` и `get_changelist_form`); `fields = ("name", "parent", "icon", "image", "sort_order", "is_active")` (как у родителя), `readonly_fields = ("name", "parent", "is_active")`; `list_editable = ("sort_order",)`; `list_filter = ("is_active",)`; `get_queryset` — выборка родителя с `select_related("parent")`, отфильтрованная `parent__name=settings.ROOT_CATEGORY_NAME, parent__parent__isnull=True` (комментарий: тот же круг, что `homepage_categories_q`, без `sort_order`); `_get_obj_does_not_exist_redirect` → `Http404("Категория не найдена")` (как 42.4/42.5 — карточка вне выборки неотличима от несуществующей); `get_form` родителя (ставит `help_text` картинки) наследуется как есть; `view_on_site = False`; `save_model` → хелпер с `CATEGORY_FIELDS`. Родительский `parent` в списке (`list_display`) — readonly-FK на `products.Category`, которой на сайте нет: Django выведет текст без ссылки; проверить в AC12, что ссылок `/admin/` нет.
    - Регистрация: `marketing_site.register(Product, …)`, `(Brand, …)`, `(HomepageCategory, …)`. Импорт модуля в `ProductsConfig.ready()` рядом с `signals`.

- [x] **Task 4a — очистка HTML новостей и блога** (AC16; решение 19)
  - [x] Новый модуль `apps/common/utils/html_sanitizer.py`: перенести из `apps/pages/models.py` `_STRIP_BLOCKS_RE` и белый список (теги, атрибуты, протоколы) константами модуля: `RICH_HTML_TAGS` — страничный список без `meta` и `link`; `RICH_HTML_ATTRIBUTES` — без ключей `meta` и `link`. Функция `sanitize_rich_html(html: str, *, tags=RICH_HTML_TAGS, attributes=RICH_HTML_ATTRIBUTES) -> str`: пустое значение вернуть как есть, затем удалить блоки, затем `bleach.clean(..., protocols=["http", "https", "mailto"], strip=True)`. Docstring — путь атаки решения 19 одной фразой.
  - [x] `apps/pages/models.py`: `Page.save` зовёт `sanitize_rich_html(self.content, tags=PAGE_HTML_TAGS, attributes=PAGE_HTML_ATTRIBUTES)`, где страничные списки — общие плюс `meta` и `link` с прежними атрибутами. Порядок в `save()` не меняется: удаление блоков, затем `seo_description`, затем очистка; повторное удаление блоков в хелпере идемпотентно. Итоговый HTML страниц — байт в байт прежний.
  - [x] `apps/common/models.py`: `save()` у `News` и `BlogPost` — `self.content = sanitize_rich_html(self.content)`, то же для `excerpt`, затем `super().save(*args, **kwargs)`. Если `save` вызван с `update_fields` без `content`/`excerpt`, поле не очищается и не пишется — это нормально.
  - [x] GitNexus `impact` по `Page.save` до правки — сообщить blast radius Alex.

- [x] **Task 4b — избранные бренды на главной сразу** (AC7; решение 13)
  - [x] GitNexus `impact` по `_revalidate_nextjs`, `invalidate_page_cache`, `invalidate_featured_brands_cache_on_save` до правки — blast radius Alex.
  - [x] Новый модуль `apps/common/services/nextjs_revalidate.py`: `revalidate_nextjs_path(path: str) -> None` — тело `_revalidate_nextjs` из `apps/pages/signals.py` без изменений (настройки, `requests.post(..., timeout=10)`, четыре исхода в лог); `revalidate_nextjs_path_in_background(path: str) -> None` — `threading.Thread(target=revalidate_nextjs_path, args=(path,), daemon=True).start()`. Константа `HOME_PAGE_PATH = "/home"` с комментарием: маршрут `(blue)/home`, `/` — динамический редирект и в ISR не участвует.
  - [x] `apps/pages/signals.py`: `_invalidate_page_cache_now` зовёт `revalidate_nextjs_path_in_background(f"/{slug}")`; `_revalidate_nextjs`, импорты `requests`/`threading` убрать. Поведение страниц прежнее.
  - [x] `apps/pages/tests.py`: `RevalidateNextjsTest` → `tests/unit/test_nextjs_revalidate.py` (патч `apps.common.services.nextjs_revalidate.requests.post`, логгер `apps.common.services.nextjs_revalidate`), проверки и ожидания прежние (решение 13).
  - [x] `apps/products/signals.py`: в `invalidate_featured_brands_cache_on_save` и `…_on_delete` общий хелпер `_on_featured_change(was_featured: bool, is_featured: bool)` — `on_commit` со сбросом `FEATURED_BRANDS_CACHE_KEY` (как сейчас) и, если `was_featured or is_featured`, с `revalidate_nextjs_path_in_background(HOME_PAGE_PATH)`. Условия сброса кэша API не меняются: те же три ветки и `_FEATURED_RELEVANT_FIELDS`. `track_brand_previous_state` дополнительно читает `is_featured` (он уже в `_FEATURED_RELEVANT_FIELDS`).
  - [x] Тесты в `tests/unit/test_nextjs_revalidate.py`: бренд стал избранным, перестал избранным, избранный изменён, неизбранный изменён (сброса нет), неизбранный изменён через `queryset.update` (сигналов нет), создание и удаление избранного и неизбранного; откат транзакции — сброса нет. `revalidate_nextjs_path_in_background` патчится в `apps.products.signals`. Плюс интеграционный AC7: POST бренда в `/marketing/` → вызов с `"/home"` после commit.

- [x] **Task 5 — nginx и smoke-проверки** (AC14; решение 18)
  - [x] `docker/nginx/conf.d/default.conf` и `local.conf`: `location /marketing/` — копия соседней `location /manager/` (в `default.conf` — с таймаутами и `include /etc/nginx/snippets/app-headers.conf`), комментарий «Раздел маркетинга (стори 42.6)». `docker/nginx/snippets/app-headers.conf:2` — дописать `/marketing/` в перечень.
  - [x] `tests/unit/test_nginx_security_headers.py`: `("default.conf", "/marketing/")` в параметры `test_known_location_is_covered`; `TestManagerSectionRoute.test_manager_location_proxies_to_backend` параметризовать локацией (`/manager/`, `/marketing/`) — существующие проверки `/manager/` сохраняются.
  - [x] `scripts/deploy/check-manager-route.sh`: необязательный второй аргумент `SECTION` (по умолчанию `manager`, допустимы только `[a-z]+` — иначе выход с ошибкой); все пути и сообщения — через `$SECTION`; шапка-комментарий — про оба раздела. `tests/unit/test_check_manager_route_script.py`: `run_script` получает необязательную секцию; `test_section_routed_to_django_passes` и `test_broken_route_fails` параметризовать секциями `manager` (без аргумента — прежний вызов) и `marketing`; отдельный тест — недопустимое имя раздела.
  - [x] `scripts/deploy/release-has-manager-route.sh`: необязательный второй аргумент — раздел (по умолчанию `manager`, проверка `[a-z]+`), маркер `path("$SECTION/", ${SECTION}_site.urls)`. `tests/unit/test_release_has_manager_route_script.py`: те же сценарии для `marketing` (релиз до раздела — urls.py только с `manager/`).
  - [x] `.github/workflows/main.yml` (шаг «Маршрут /manager/ через nginx»): в `check_section` добавить `bash scripts/deploy/check-manager-route.sh "$1" marketing`; имя шага и комментарий — про оба раздела. `wait_ready` не менять.
  - [x] `.github/workflows/deploy.yml:543-557`: тот же блок для `marketing` — `release-has-manager-route.sh "$RELEASE" marketing`, при коде 1 — «релиз раньше раздела /marketing/», иначе `check-manager-route.sh "$PRODUCTION_URL" marketing`.
  - [x] **`.sh` — только LF** (`.gitattributes` с PR #313). Тесты скриптов гонять в контейнере.

- [x] **Task 6 — тесты** (NFR-42-01, NFR-42-02: у каждой проверки доступа негативный тест)
  - [x] `backend/tests/integration/test_marketing_section.py` (integration). Хелперы и autouse-фикстуры — явным импортом из `tests.integration.test_manager_clients_section`: `role_groups`, `make_staff_member`, `form_payload`, `message_texts`, `PASSWORD`, `get_unique_suffix`. **Не `import *`** и не `no_routing_rules`/`verified_email_task`, если не нужны: клиенты в стори не создаются. Нового общего модуля хелперов не заводить (правило 42.4). Свои фикстуры:
    - `marketer`, `marketer_client`; `section_member` параметризован группами «Маркетинг» и «Руководители» (как 42.4);
    - `media_root` (autouse, `settings.MEDIA_ROOT = tmp_path`) — загрузки логотипов и картинок не пишутся в рабочий `media/`; картинка — `SimpleUploadedFile` с настоящим PNG от Pillow;
    - `showcase` — якорь `ROOT_CATEGORY_NAME` (через `settings.ROOT_CATEGORY_NAME`, не литерал), два корня витрины, подкатегория, категория вне якоря (`CategoryFactory`);
    - `make_product(**overrides)` — `ProductFactory` + вариант `ProductVariantFactory` с `main_image` по необходимости (`apps/products/factories.py`).
  - [x] Сценарии:
    - AC1 — матрица входа по `/marketing/` и `/marketing/products/product/` (как `TestEntry` 42.4), «FREESPORT — Маркетинг» в HTML.
    - AC2 — POST форм добавления рубрики, новости, статьи, баннера через `form_payload` GET-страницы `add/`; затем `APIClient().get(...)` публичных эндпоинтов (баннер — `type=marketing`; кэш баннеров сбрасывает сигнал); негативные: будущая дата публикации, неопубликованная статья, истёкший баннер. Нет `view_on_site` в контексте/HTML карточек.
    - AC3 — четыре рубрики, удаление из карточки (GET — protected в контексте, POST — объект на месте) и массовым действием; выбор «родитель + ребёнок с новостью».
    - AC4 — колонки (`label_for_field` или `<th>`), фильтры (`cl.filter_specs`), имена полей строк `form-N-<метка>`, `action_form.fields["action"].choices` — ровно десять, сохранение списка (`_save` + management form) и массовое действие; отсутствие цен/`onec_id`/НДС в HTML.
    - AC5 — `adminform.form.fields` = ровно пять меток; скрытые поля — нет `name="<поле>"` и подписи `verbose_name`; нет `variants-TOTAL_FORMS`/формсета изображений; ссылка бренда в раздел; подделанный POST.
    - AC6 — `patch.object(Product, "save", autospec=True, side_effect=Product.save)` и `call_args.kwargs["update_fields"]`; «импорт во время открытой карточки» — `Product.objects.filter(pk=…).update(name=…, description=…)` между GET и POST; стоп-кадр списка: GET списка → `update()` метки X → POST с данными GET, где изменена только строка Y. То же для бренда и категории главной.
    - AC7 — POST бренда с логотипом и флагом; `/api/v1/brands/featured/` (`BrandViewSet.featured`, `products/views.py`, кэш `FEATURED_BRANDS_CACHE_KEY`); ошибка без логотипа по-русски; отсутствие привязок, колонки, действия.
    - AC8 — состав списка по `showcase`; правка порядка в списке и иконки/картинки в карточке; подделанные POST карточки и списка с `is_active` — активность прежняя; `/api/v1/categories/?is_homepage=true` (`CategoryFilter.filter_is_homepage`, `products/filters.py:520`); 404 на подкатегорию и категорию вне якоря.
    - AC9 — подписчики `Newsletter.objects.create(...)` и `update(subscribed_at=…)`; границы 30 дней с `patch("django.utils.timezone.now")` (`freezegun` нет, зависимость не заводить); состав блоков `response.context["app_list"]`.
    - AC10 — матрица прямых URL маркетолога; `add`/`delete` → 403.
    - AC11 — `group.permissions.set([...view-права...])`: карточки без полей ввода, списки без полей строк, POST → 403, действий меток нет; подделанный POST действия (`action=mark_as_hit`) — товар не изменён.
    - AC12 — `'href="/admin/' not in html` для главной (после сохранения товара), списков и карточек семи моделей, истории товара; редиректы `_save`/`_continue`; «+» рубрики в карточке новости.
    - AC13 — `CaptureQueriesContext`: 5 → 50 товаров (с вариантами и фото, в категориях четвёртого уровня), 5 → 50 категорий глубиной 4 в фильтре, брендов, корней витрины, подписчиков (образец — `TestQueryCount` 42.5).
    - AC16 — POST добавления новости и статьи с вредным и разрешённым HTML в `content` и `excerpt` через `/marketing/` и `/admin/`; проверки по БД и по ответу детального API; ожидаемые подстроки литералами.
  - [x] `backend/tests/unit/test_html_sanitizer.py` (unit): каждый вредный фрагмент AC16 по отдельности; `<style>` и `<script>` удаляются вместе с содержимым; разрешённая разметка без изменений; пустая строка; `meta`/`link` удаляются общим списком и сохраняются страничным.
  - [x] `backend/tests/unit/test_marketing_admin_site.py` (unit, `RequestFactory`): `MarketingAdminSite.has_permission` по ролям; кэш — один запрос к группам на два вызова; один `request` на двух сайтах не путает доступ (менеджер: `/manager/` — да, `/marketing/` — нет, в любом порядке вызовов); состав `marketing_site._registry` — ровно семь моделей решения 5; `admin.site._registry` — по-прежнему родительские классы для `Product`, `Brand`, `HomepageCategory`, `Banner`, `News`, `BlogPost`, плюс `ContentCategoryAdmin` для `common.Category`; `newsletter_stats` на пустых данных; `get_readonly_fields`/`get_fieldsets` товара и бренда не содержат скрытых полей (страж белого списка); у всех десяти действий `ProductAdmin` `allowed_permissions == ("change",)`.
  - [x] **Тесты транзакционные** (как 42.4/42.5): autouse `clear_db_before_test(transactional_db)` в `tests/conftest.py`; правки прав группы стирает `flush`, `role_groups` следующего теста создаёт группы заново. `on_commit` сигналов кэша срабатывает.
  - [x] **Проверка мутациями** — по каждой защите временно убрать её, убедиться, что падает названный тест, вернуть. Итог — в Debug Log:

    | Убрать | Должен упасть |
    |---|---|
    | `is_superuser` в `StaffSectionAdminSite.has_permission` | AC1 (суперпользователь в группе) |
    | ключ кэша по `self.name` → общий атрибут | unit: один `request` на двух сайтах |
    | `SUPERVISORS_GROUP` из `section_groups` маркетинга | AC1 (руководитель) |
    | `protected` в `ContentCategoryAdmin.get_deleted_objects` | AC3 |
    | `permissions=["change"]` у `mark_as_hit` | AC11, unit `allowed_permissions` |
    | `"description"` в `fieldsets` товара (не в `readonly`) | AC5 (поле в HTML, подделанный POST) |
    | `save_model` товара → `super().save_model(...)` | AC6 (`update_fields`, импорт затёрт) |
    | `show_hidden_initial` в `SeenValuesForm` | AC6 (стоп-кадр списка) |
    | `get_changelist_form` товара → родительский | AC6 (стоп-кадр списка) |
    | фильтр корней витрины в `get_queryset` категорий | AC8 (подкатегория в списке, 404) |
    | `list_editable` категорий → родительский `("sort_order", "is_active")` | AC8 (`form-N-is_active`, подделанный POST списка) |
    | `is_active` убран из `readonly_fields` категорий | AC8 (`name="is_active"` в карточке, подделанный POST) |
    | `actions = []` у брендов | AC7 (действие объединения) |
    | `prefetch` фото → обращение к `obj.variants` в `photo` | AC13 |
    | граница 30 дней `gte` → `gt` или сдвиг на сутки | AC9 (границы) |
    | `{% block sidebar %}{% endblock %}` в шаблоне главной | AC12 (главная после правки) |
    | `view_on_site = False` у новостей | AC2/AC12 |
    | `"category_name"` → `"category"` в `list_display` товара | AC13 (число запросов растёт с числом товаров) |
    | `CategoryPathListFilter` → штатный `"category"` в `list_filter` | AC13 (число запросов растёт с числом категорий) |
    | `sanitize_rich_html` в `News.save` | AC16 (новость), unit не падает — проверка именно интеграцией |
    | `excerpt` в `BlogPost.save` | AC16 (`excerpt` статьи) |
    | `meta`/`link` вернуть в `RICH_HTML_TAGS` | AC16, unit |
    | удаление блоков до bleach | unit (текст CSS остался) |
    | условие `was_featured or is_featured` → всегда сбрасывать | unit «неизбранный изменён — сброса нет» |
    | вызов сброса `/home` в сигнале брендов | unit «стал избранным», AC7 |
    | `on_commit` → прямой вызов сброса | unit «откат транзакции — сброса нет» |

- [x] **Task 7 — существующие тесты и проверки**
  - [x] Без правок зелёные: `tests/integration/test_manager_clients_section.py`, `tests/integration/test_manager_orders_section.py`, `tests/unit/test_manager_admin_site.py`, `tests/unit/test_manager_orders_admin.py` (рефакторинг `has_permission`), `tests/unit/test_admin/test_products_admin.py`, `apps/products/tests/test_admin_homepage_category.py`, `apps/products/tests/unit/test_admin_onec_deleted.py`, `apps/banners/tests/test_admin.py`, `apps/banners/tests/test_mobile_image.py`, `tests/unit/test_staff_role_groups_migration.py`, `tests/unit/test_nginx_security_headers.py` (только добавленные параметры), тесты скриптов (только добавленные сценарии), `tests/integration/test_pages_api.py` (перенос санитайзера страниц, решение 19), `apps/pages/tests.py` (кроме переноса `RevalidateNextjsTest`, решение 13), тесты новостей и блога в `tests/` и `apps/common/tests/`, тесты сигналов брендов (`FEATURED_BRANDS_CACHE_KEY`). Исключение — `test_brand_model.py:93` (решение 13).
  - [x] Полный backend-прогон в Docker, один compose-проект: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -n 4 -q -p no:sugar -m "not performance and not slow"` (~16 мин, ориентир после 42.5 — 4314 passed, 76 skipped). В фоне.
  - [x] Линтеры строго после зачётного pytest, в том же `-p freesport-test`: `black --check .`, `isort --check-only .`, `flake8`, `mypy .`. Базис — ноль ошибок (после 42.5: black 473 unchanged, mypy 626 файлов).
  - [x] `makemigrations --check --dry-run` — миграций нет. `check_openapi_sync` не нужен: API не меняется.
  - [x] `npx gitnexus detect-changes --scope all -r "C:\Users\1\DEV\FREESPORT"` — затронуты только символы этой стори.
  - [x] Completion Notes: отклонения от стори с причиной; ответы Alex на вопросы ниже (если получены до разработки); шаги выката для Alex.

### Review Findings

Ревью 16.10.2026: `6b0d536f...9a7b706f` без `_bmad-output/` (3752 строки диффа), режим `full`, четыре слоя через плагин Codex: `blind-hunter`, `edge-case-hunter`, `verification-gap`, `acceptance-auditor`. Все слои завершились. Получено 20 исходных замечаний, после объединения повторов — 14; каждое проверено по коду до объединения. Итог: 0 решений владельца, 1 исправление, 0 отложенных, 13 отклонённых. Индекс GitNexus актуален на `9a7b706`. Код приложения при ревью не менялся.

#### Исправления

- [x] [Review][Patch] **R42.6-1, low: тест миниатюр не проверяет адрес картинки** [`backend/tests/integration/test_marketing_section.py:1219-1232`]. Тест числа запросов считает только `<img ` в ответе; ни один тест не сверяет `src` с `_product_photo_url` (`backend/apps/products/marketing_admin.py:178-190`). Возврат `/products/b.png` вместо `/media/products/b.png` или потеря приоритета фото варианта над `base_images` пройдут незамеченными. Добавить параметризованный тест строки списка: фото варианта важнее `base_images`; `/products/…` → `/media/products/…`; `/media/…` и `http(s)://…` без изменений; прочий относительный путь → `/media/<путь>`.

#### Отклонённые замечания

- blind-hunter + edge-case-hunter + verification-gap + acceptance-auditor, `low`: устаревшая карточка бренда сохраняет избранный бренд без логотипа (`marketing_admin.py:193-227`). Подтверждено: при `show_hidden_initial` форма валидирует отправленное `is_featured=False`, а `save(update_fields=["image", …])` оставляет в БД `True` коллеги. На сайте последствий нет: `/brands/featured/` исключает бренды без картинки (`products/views.py:468-471`); следующее сохранение карточки упрётся в «Для показа на главной нужен логотип». Нужны одновременные правки двух сотрудников, исправление добавляет ветку сверки с БД.
- acceptance-auditor, `low`: сигнал бренда берёт `instance.is_featured` из устаревшей формы и при `update_fields` без флага делает лишний сброс `/home` и кэша featured. Последствие — один лишний запрос в Next; тот же редкий сценарий двух вкладок.
- acceptance-auditor, отклонено (правка спецификации): в `local.conf` у `/marketing/` нет `include app-headers.conf`. Ни одна проксируемая локация `local.conf` (`/api/`, `/admin/`, `/manager/`) сниппет не подключает; решение 18 требует копию `/manager/`. Расхождение — в формулировке AC14, а не в коде.
- blind-hunter, `false`: удаление родителя вместе с выбранной дочерней рубрикой (`common/admin.py:557`). Явно выбранная рубрика — не тихий каскад; новости обеих и невыбранные внуки попадают в `protected`. AC3 этот случай не запрещает, комментарий в коде описывает его как намеренный.
- blind-hunter + edge-case-hunter, `low`: гонка между проверкой `get_deleted_objects` и удалением рубрики. Окно — миллисекунды между двумя запросами одного POST; блокировка добавляет транзакционную логику ради маловероятного случая.
- blind-hunter, `false`: старый HTML новостей и блога в БД не очищен. До 42.6 HTML писал только суперпользователь (решение 19), недоверенного содержимого в базе нет.
- blind-hunter, `false`: `update()`/`bulk_*` обходят санитайзер. Ни один путь записи раздела и `/admin/` не пишет `content`/`excerpt` через `QuerySet.update`; комментарий перечисляет именно эти пути.
- blind-hunter, `low`: неограниченные потоки сброса ISR. Число потоков ограничено числом избранных брендов в одной транзакции; схема перенесена из `pages/signals.py` без изменений.
- blind-hunter, `low`: нет повторной доставки сброса. Спецификация (решение 13) принимает худший случай — бренд появится через час, как до стори.
- edge-case-hunter, `low`: `Thread.start()` с `RuntimeError` в `on_commit` даёт 500. Исчерпание лимита потоков процесса на сохранении бренда не показано.
- blind-hunter + verification-gap, `low`: вход маркетолога через nginx с настоящей сессией не проверяется. Локация — копия `/manager/`, которую проверяет `check-manager-session.sh` на обоих конфигах; этот скрипт заточен под клиентов менеджера, для маркетинга нужен новый.
- blind-hunter, `false`: матрица «только `view_*`» не покрывает баннеры, новости, блог и рубрики. AC11 ограничен товарами, брендами и категориями главной; остальные модели работают родительскими классами со штатной проверкой прав Django.
- blind-hunter + verification-gap, `low`: сброс ISR `/home` проверен только через подмены. Худший случай по спецификации — задержка до часа, как до стори; e2e требует стенда с production-сборкой Next. Рекомендация для выката: после первого сохранения избранного бренда на проде найти в логе backend строку `Next.js revalidation triggered for /home`.

## Dev Notes

### Текущее состояние кода (сверено на `6b0d536f`)

| Место | Сейчас | Что меняется |
|---|---|---|
| `backend/freesport/admin_site.py:37-88` `ManagerAdminSite` | `has_permission` с кэшем `request._manager_site_access`, `index` с очередью, `get_app_list` («Клиенты») | `has_permission` → базовый `StaffSectionAdminSite`; + `MarketingAdminSite`, `marketing_site` |
| `backend/freesport/urls.py:48-50` | `admin/`, `manager/` | + `marketing/` |
| `backend/templates/admin/manager/index.html` | очередь + пустой `sidebar` | образец для `admin/marketing/index.html`, не меняется |
| `backend/templates/admin/index.html` | блоки приложений по `app_label` (`products, integrations, common, orders, …`, остальные — в конце) | не меняется: на маркетинге порядок «Товары», «Новости и блог», «Баннеры» |
| `backend/apps/users/migrations/0023_staff_role_groups.py:37-62` | права «Маркетинг»: `banners.*_banner`, `common.*_news/_blogpost/_category`, `products.view/change_product`, `view/change_brand`, `view/change_homepagecategory` | не меняется; своей миграции прав стори не добавляет |
| `backend/apps/banners/admin.py:18-148` `BannerAdmin` | полный набор полей, превью | наследуется, не меняется |
| `backend/apps/common/admin.py:275-302` `NewsletterAdmin` | список подписок | не меняется, на маркетинге не регистрируется |
| `backend/apps/common/admin.py:347-521` `NewsAdmin`, `BlogPostAdmin` | `formfield_for_foreignkey` — только активные рубрики; `prepopulated_fields` slug | наследуются, не меняются |
| `backend/apps/common/models.py:427` `Category` | `parent` — `CASCADE`; `get_absolute_url` → `common:category-detail` (такого URL нет) | + `ContentCategoryAdmin` на двух сайтах |
| `backend/apps/common/models.py:755`, `:849` `News`, `BlogPost` | `News.category` — `CASCADE`, `BlogPost.category` — `SET_NULL`; `BlogPost.get_absolute_url` → `reverse("blog-detail")` без namespace (`:957`) | не меняются; отсюда решения 6 и 7 |
| `backend/apps/common/apps.py:48` `CommonConfig` | без `ready()` | + `ready()` |
| `backend/apps/products/admin.py:80-204` `BrandAdmin` | инлайн привязок 1С, аннотация `mappings_count`, действие `merge_brands` | наследуется, не меняется |
| `backend/apps/products/admin.py:322-366` `HomepageCategoryAdmin` | все категории, `list_editable` `sort_order`/`is_active`, без add/delete | наследуется, не меняется |
| `backend/apps/products/admin.py:370-576` `ProductAdmin` | цены/1С/НДС в списке, инлайны вариантов и изображений, десять действий меток без `permissions` | + `permissions=["change"]` у действий |
| `backend/apps/products/models.py:35-120` `Brand` | `clean` (`:70`, английское сообщение `:75`), `save` пересчитывает `normalized_name` | текст сообщения |
| `backend/apps/products/models.py:265-541` `Product` | метки `:329-374`, `discount_percent` `:375` | не меняется |
| `backend/apps/products/filters.py:486` `homepage_categories_q` | дети якоря с `sort_order > 0` | не меняется, круг повторяется в разделе |
| `backend/apps/products/signals.py` | сброс кэша featured-брендов на `save`/`delete` бренда (`on_commit`) | не меняется |
| `backend/apps/products/models.py:240-249` `Category.__str__`/`full_name` | рекурсия по `parent`, запрос на уровень | не меняется; в разделе не вызывается (решение 12) |
| `backend/apps/pages/models.py:16`, `:61-155` `Page.save` | `_STRIP_BLOCKS_RE` + `bleach.clean` со своим белым списком | список и логика → `apps/common/utils/html_sanitizer.py`, поведение прежнее (решение 19) |
| `backend/apps/common/models.py` `News`, `BlogPost` | без `save()`, HTML не очищается | + `save()` с `sanitize_rich_html` для `content`, `excerpt` |
| `frontend/src/app/(blue)/news/[slug]/page.tsx:121`, `blog/[slug]/page.tsx:130` | `dangerouslySetInnerHTML` без очистки | не меняется; защита на бэкенде |
| `frontend/src/app/(blue)/home/page.tsx:15` | `revalidate = 3600`, featured-бренды рендерятся на сервере | не меняется; ISR `/home` сбрасывается сигналом брендов (решение 13) |
| `frontend/src/app/api/revalidate/route.ts` | `POST` с `x-revalidate-secret`, `revalidatePath(path)` | не меняется |
| `backend/apps/pages/signals.py` `_revalidate_nextjs` | сброс ISR страницы после commit, в потоке | → `apps/common/services/nextjs_revalidate.py` |
| `backend/apps/products/signals.py` | сброс `FEATURED_BRANDS_CACHE_KEY` по изменению релевантных полей | + сброс ISR `/home` для избранных брендов |
| `docker/nginx/conf.d/default.conf:227`, `local.conf:83` | `location /manager/` | + `location /marketing/` |
| `scripts/deploy/check-manager-route.sh`, `release-has-manager-route.sh` | только `/manager/` | + необязательный аргумент раздела |
| `.github/workflows/main.yml:203-330`, `deploy.yml:543-557` | проверка `/manager/` | + `/marketing/` |

### Подводные камни

- **`prepopulated_fields` родителя без поля в форме** — `AdminForm` строит `form[field_name]` по каждому ключу (`helpers.py:50-53`) и падает `KeyError`. У товара и бренда в разделе `prepopulated_fields = {}`.
- **`list_editable` и права.** Без `change` Django сам не строит формсет строк и отвечает 403 на `_save` (`options.py:2101-2102`, `:2138`). Действия — другое дело: без `allowed_permissions` они доступны любому, кто видит список (решение 9).
- **Сохранение `list_editable` зовёт `save_model`** для каждой изменённой строки — поэтому хелпер решения 10 закрывает и список, и карточку. Строки берутся заново из `get_queryset` раздела (`_get_list_editable_queryset`), чужой id из подделанного POST категорий главной не пройдёт.
- **Форма строки списка — не `ModelAdmin.form`.** `get_changelist_form` строит свою `modelform_factory` (`options.py:901`), поэтому `SeenValuesForm` передаётся туда явно через `form=`.
- **`show_hidden_initial` в формсете** рендерит `initial-form-N-<поле>`; `BooleanField.to_python("False")` → `False`. Подделанный POST без скрытого поля сравнивается с `None` → снять флажок так нельзя, поставить можно — защиты это не ослабляет.
- **`HomepageCategory.is_active` — это `products.Category.is_active`** (proxy, одна таблица): снять активность — убрать категорию с сайта целиком, поэтому в разделе поле только для чтения (решение 14). Родитель `HomepageCategoryAdmin` держит его в `list_editable` — не забыть переопределить и `list_editable`, и `readonly_fields`.
- **Иконка важнее картинки** на главной (`CategoriesSection.tsx:80-81`) — поэтому `icon` правится.
- **`News.updated_at` — `auto_now_add`** (`common/models.py:823`), дата обновления новости не меняется при правке. Существующий дефект модели, стори его не чинит (модели не меняются).
- **Кэш баннеров** сбрасывается сигналом при сохранении (`banners/signals.py`); тест AC2 читает API после сохранения — кэш не мешает. Кэш featured-брендов — `on_commit`, в транзакционных тестах срабатывает.
- **Читать HTML на «Описание».** Подпись «Описание» есть и у бренда, и у краткого описания товара — в тестах скрытых полей товара проверять `name="description"` и полные подписи (`Технические характеристики`, `Ставка НДС (%)`, `ID товара в 1С (SKU)`, `Скрыт импортом 1С`), а не короткое слово.
- **Сессия общая для `/admin/`, `/manager/`, `/marketing/`** — суперпользователь на `/marketing/` видит вход с «нет доступа», это штатно (решение 2).
- **Суперпользователь в `/admin/` по-прежнему видит полные `ProductAdmin`/`BrandAdmin`** с ценами, 1С и объединением брендов — решение 5 стори 42.1 («перестройка основной `/admin/` — Non-goal»).

### Выкат (для Completion Notes и Alex)

1. Ручных шагов в базе нет. Деплой сам делает `nginx -t` и `nginx -s reload` (`deploy.yml`), новая локация уходит с релизом; после рестарта backend деплой перезапускает nginx (memory: nginx держит старый IP upstream).
2. После выката: `curl -sI https://optisport.ru/marketing/` → 302, `Location: /marketing/login/?next=/marketing/`. 404 от Next — nginx не перечитал конфиг: `docker compose exec nginx nginx -s reload`.
3. Перед тем как заводить маркетологов, владелец открывает в `/admin/` каждую из 3 новостей и 3 статей и сохраняет её: первое сохранение очищает HTML (решение 19). Затем проверяет страницы новостей и блога на сайте глазами: у трёх записей-документов пропадёт встроенный `<style>`.
4. Проверка сброса главной (решение 13): в `/admin/` у любого избранного бренда сохранить описание без изменения флага — в логе backend `Next.js revalidation triggered for /home` (`docker compose … logs backend | grep "Next.js revalidation"`). `skipped`/`rejected: HTTP 401` — сверить `FRONTEND_INTERNAL_URL` и `REVALIDATE_SECRET` у backend и frontend в `.env.prod`. Сайт при этом работает, бренды обновляются раз в час, как до стори.
5. Владелец заводит маркетологов в `/admin/`: `is_staff=True`, группа «Маркетинг». Учётной записи `managermsk3@freesportopt.ru` с прямыми правами на баннеры (42.1, «Состояние прода») владелец по-прежнему решает сам: группа «Маркетинг» или блокировка.

### Архитектурные требования

- Django 5.2.7, DRF 3.14.0, pytest-django 4.7.0 (`backend/requirements.txt`). Новых зависимостей нет. Несколько `AdminSite` — штатный механизм Django; всё поведение сверено по исходникам 5.2.7 в `backend/venv/Lib/site-packages/django/contrib/admin/` (`options.py:901`, `:1996`, `:2101`, `:2138`; `helpers.py:50`). Веб-исследование версий не требуется.
- Миграции, API, OpenAPI, фронтенд не меняются. Модели меняются только поведением `save()` (`News`, `BlogPost`, решение 19) и текстом `Brand.clean`. Санитайзер — `bleach==6.2.0`, он уже есть в `requirements.txt`. Меняются nginx-конфиги и CI/деплой-скрипты (решение 18).
- Язык: интерфейс, сообщения, комментарии, docstrings — русский (NFR-42-03).

### Тестирование

- Только Docker + PostgreSQL: `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -xvs <путь>`; `--env-file` не передаётся; параллельные прогоны в одном compose-проекте запрещены (deadlock на TRUNCATE).
- Маркеры по каталогу: `tests/unit/` → `unit`, `tests/integration/` → `integration`. Новый каталог под `tests/` не заводить.
- Проверки доступа — критический модуль, покрытие ≥ 90 % (NFR-42-01): `freesport/admin_site.py`, три модуля `marketing_admin.py`, `ContentCategoryAdmin`.
- Тесты скриптов (`test_check_manager_route_script.py`, `test_release_has_manager_route_script.py`) скипаются без `bash`/`curl`/`git` — в контейнере они есть, прогонять там.

### Уроки 42.4 и 42.5

- Ревью 42.4 — 37 замечаний, 42.5 — 27 за семь кругов. Повторяющиеся классы: (1) «прочитал — записал полным `save()`» и потерянные правки двух вкладок (R42.4-1, R42.5-1), (2) тесты, которые не падают при удалении защиты, (3) действия без проверки прав, (4) эталон теста из константы реализации (R42.5-7). Здесь: (1) — решения 10–11 и AC6, отказ от отклонения устаревшей формы обоснован в решении 11 — ссылаться на него ревьюеру; (2) — таблица мутаций; (3) — решение 9, AC11; (4) — ожидаемые колонки, подписи и тексты в тестах — литералами.
- Readonly-FK в карточке раздела — только display-методом (решение 12 стори 42.4).
- Блок «Последние действия» на главной раздела убирается (решение 13 стори 42.4).
- Отклонения от стори — в Completion Notes с причиной, не молча.
- Вывод `isort` не смотреть через `tail` (R42.5-D3: файлов было 22, а не 4–7).

### Связь с последующими стори

- **42.7** — раздел руководителя: управление сотрудниками (в том числе маркетологами), отказ маркетологу на URL раздела руководителя (AC10 здесь его не проверяет). Базовый `StaffSectionAdminSite` пригодится, если у руководителя будет свой сайт.
- **42.9** — лента журнала по перечню `section-contents.md`; действий маркетинга в нём нет (решение 15).

### Project Structure Notes

- Новые файлы:
  - `backend/apps/banners/marketing_admin.py`;
  - `backend/apps/common/marketing_admin.py`;
  - `backend/apps/products/marketing_admin.py`;
  - `backend/templates/admin/marketing/index.html`;
  - `backend/tests/integration/test_marketing_section.py`;
  - `backend/tests/unit/test_marketing_admin_site.py`;
  - `backend/apps/common/utils/html_sanitizer.py`;
  - `backend/tests/unit/test_html_sanitizer.py`;
  - `backend/apps/common/services/nextjs_revalidate.py`, `backend/tests/unit/test_nextjs_revalidate.py`.
- Изменяемые:
  - `backend/apps/pages/signals.py`, `backend/apps/pages/tests.py` (перенос `RevalidateNextjsTest`), `backend/apps/products/signals.py`;
  - `backend/apps/pages/models.py` (санитайзер — через общий хелпер), `backend/apps/common/models.py` (`save()` у `News`, `BlogPost`);
  - `backend/freesport/admin_site.py`, `backend/freesport/urls.py`;
  - `backend/apps/banners/apps.py`, `backend/apps/common/apps.py`, `backend/apps/products/apps.py`;
  - `backend/apps/common/admin.py` (`ContentCategoryAdmin`), `backend/apps/products/admin.py` (`permissions` действий), `backend/apps/products/models.py` (текст `Brand.clean`);
  - `backend/apps/products/tests/test_brand_model.py` (одно ожидание);
  - `docker/nginx/conf.d/default.conf`, `docker/nginx/conf.d/local.conf`, `docker/nginx/snippets/app-headers.conf` (комментарий);
  - `scripts/deploy/check-manager-route.sh`, `scripts/deploy/release-has-manager-route.sh`;
  - `backend/tests/unit/test_nginx_security_headers.py`, `test_check_manager_route_script.py`, `test_release_has_manager_route_script.py` (новые параметры);
  - `.github/workflows/main.yml`, `.github/workflows/deploy.yml`;
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`, этот файл.

### References

- Эпик: `_bmad-output/planning-artifacts/epic-42-staff-admin-sections.md` — Story 42.6, FR-42-18…23, NFR-42-01…04, Additional Requirements («Описание товара перезаписывает импорт 1С», «Назначение скидки исключено»), UX Design Requirements (заголовок раздела называет роль, главная по образцу `index.html`).
- Спецификация: `_bmad-output/specs/spec-staff-admin-sections/SPEC.md` (CAP-4, Constraints «Скрытие полей», «Описание товара маркетингу не даётся», Non-goals, Assumptions — `/marketing/`), `section-contents.md` («Маркетинг», «Товары (маркетинговый вид)», «Ни одной из ролей»), `affected-code.md` («Модели и admin-классы разделов», «Конфликты с 1С»), `.memlog.md` (решения 08.10.2026: статические страницы и список подписчиков — не маркетингу, скидка — только чтение).
- Предыдущие стори: `Story/42-1-…md` (наборы прав «Маркетинг», proxy-права `HomepageCategory`), `Story/42-4-…md` (решения 1–13: отдельный сайт, вход, 404, белый список, readonly-FK, главная без «Последних действий», nginx), `Story/42-5-…md` (решения 5, 11; `ManagerOrderForm` и `show_hidden_initial`; R42.5-1…27).
- Код: `backend/freesport/admin_site.py`, `backend/freesport/urls.py`, `backend/apps/{banners,common,products}/admin.py`, `backend/apps/common/models.py:427-960`, `backend/apps/products/models.py:35-541`, `backend/apps/products/filters.py:486`, `backend/apps/products/serializers.py:651`, `backend/apps/products/signals.py`, `backend/apps/products/services/variant_import.py:2343`, `backend/apps/common/services/newsletter_subscription.py:73`, `backend/apps/common/views.py:877-1135` (публичные API новостей и блога), `backend/apps/banners/models.py:372-412`, `frontend/src/components/home/CategoriesSection.tsx:80-81`, `backend/apps/orders/manager_admin.py:171-221` (`ManagerOrderForm`).
- Django 5.2.7: `contrib/admin/options.py:901` (`get_changelist_form`), `:1996` (`_get_list_editable_queryset`), `:2101-2138` (`list_editable` и права), `contrib/admin/helpers.py:50-53` (`prepopulated_fields`).
- Правила: `backend/docs/testing-standards.md`, `backend/AGENTS.md`, `project-context.md` §3–§5, `AGENTS.md` (GitNexus, Docker), `.windsurf/rules/production-operations.md` (restart nginx).

## Вопросы к Alex — закрыты 16.10.2026

1. **Активность категории на главной** — только для чтения: маркетолог меняет только категории на главной (иконка, картинка, порядок), активность категории каталога ему недоступна (решение 14, AC8). Эпик FR-42-22 и `section-contents.md` поправлены.
2. **Одновременная правка одного поля** — не критично, «последняя запись выигрывает», защиты как R42.5-1 нет (решение 11).
3. **Рубрики в `/admin/` для суперпользователя** — нужны, регистрируем (решение 7).
4. **HTML новостей и блога** — санитайзер на бэкенде (решение 19, AC16, Task 4a).
5. **Задержка до часа у избранных брендов на главной** — убрать: сброс ISR `/home` сигналом брендов через общий сервис (решение 13, AC7, Task 4b). Баннеры, категории главной, новости и блог уже обновляются сразу.
6. **Фильтр по категории в списке товаров** — по цифрам с прода оставлен со своими подписями из одного запроса (решение 12, AC13).

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (`claude-opus-5-5`), Claude Code, `bmad-dev-story`.

### Debug Log References

- GitNexus pre-flight: индекс на `6b0d536`, `git diff 6b0d536 HEAD -- backend/apps backend/freesport` пуст — переиндексация не нужна. Blast radius: `ManagerAdminSite` LOW (3 прямых импорта), `ProductAdmin`/`BrandAdmin`/`HomepageCategoryAdmin`/`BannerAdmin`/`CommonConfig`/`invalidate_page_cache`/`invalidate_featured_brands_cache_on_save` LOW (0), `NewsAdmin`/`BlogPostAdmin` LOW (1 — `urls.py`), `_revalidate_nextjs` MEDIUM (5 прямых — только тесты `RevalidateNextjsTest`, переносятся), `Page.save` — вызывающих нет, `Brand.clean` — `products/serializers.py` (validate). HIGH/CRITICAL нет.
- Проверка мутациями — скрипт в контейнере, каждая мутация на свои тесты (`pytest -x`), исходник возвращается в `finally`. **27 из 27 убиты, выживших нет:**

  | # | Мутация | Упал |
  |---|---|---|
  | 1 | `is_superuser` в `StaffSectionAdminSite.has_permission` | AC1 `superuser-in-marketing-group` |
  | 2 | кэш по `self.name` → общий ключ | unit `test_one_request_on_two_sites` |
  | 3 | `SUPERVISORS_GROUP` из `section_groups` маркетинга | AC1 (руководитель) |
  | 4 | `protected` в `ContentCategoryAdmin.get_deleted_objects` | AC3 |
  | 5 | `permissions=["change"]` у `mark_as_hit` | AC11 / unit `allowed_permissions` |
  | 6 | `"description"` в `fieldsets` товара | AC5 |
  | 7 | `save_model` товара → `super().save_model` | AC6 (`update_fields`, импорт) |
  | 8 | `show_hidden_initial` в `SeenValuesForm` | AC6 (стоп-кадр списка) |
  | 9 | `get_changelist_form` товара → родительский | AC6 (стоп-кадр списка) |
  | 10 | фильтр корней витрины в `get_queryset` | AC8 (список, 404) |
  | 11 | `list_editable` категорий → `("sort_order", "is_active")` | AC8 |
  | 12 | `is_active` убран из `readonly_fields` категорий | AC8 |
  | 13 | `actions = []` у брендов | AC7 |
  | 14 | prefetch фото → `obj.variants` в `photo` | AC13 |
  | 15 | граница 30 дней `gte` → `gt` | AC9 (ровно 30 дней) |
  | 16 | граница 30 дней + сутки | AC9 (30 дней и минута) |
  | 17 | пустой `{% block sidebar %}` | AC12 |
  | 18 | `view_on_site = False` у новостей | AC2 |
  | 19 | `"category_name"` → `"category"` в `list_display` | AC13 (товары) |
  | 20 | `CategoryPathListFilter` → штатный фильтр | AC13 (категории) |
  | 21 | `sanitize_rich_html(content)` в `News.save` | AC16 |
  | 22 | `excerpt` в `BlogPost.save` | AC16 |
  | 23 | `meta`/`link` в `RICH_HTML_TAGS` | unit санитайзера |
  | 24 | удаление блоков до bleach | unit (текст CSS) |
  | 25 | `was_featured or is_featured` → всегда | unit «неизбранный изменён» |
  | 26 | вызов сброса `/home` в сигнале | unit «стал избранным» |
  | 27 | `on_commit` → прямой вызов | unit «откат транзакции» |

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- **Сайт `/marketing/`:** `StaffSectionAdminSite` в `freesport/admin_site.py` — общая проверка входа с кэшем `request._staff_section_access[self.name]`; `ManagerAdminSite` наследует её без изменения поведения (тесты 42.4/42.5 без правок зелёные), `MarketingAdminSite` — группы «Маркетинг» и «Руководители», плашка подписчиков, переименования «Новости и блог»/«Рубрики». Шаблон главной без «Последних действий».
- **Семь моделей** на сайте маркетинга (страж — unit-тест `_registry`): баннеры, новости, статьи — родительские классы с `view_on_site = False`; рубрики — новый `ContentCategoryAdmin` (на `/admin/` и `/marketing/`) с запретом удаления рубрики с новостями или дочерними рубриками; товары, бренды, категории главной — белые списки в `apps/products/marketing_admin.py`, сохранение только изменённых полей (`save_changed_fields`) по увиденным значениям (`SeenValuesForm`, `show_hidden_initial`), `CategoryPathListFilter` из одного запроса.
- **Действия меток** `ProductAdmin` — `permissions=["change"]`.
- **Санитайзер:** `apps/common/utils/html_sanitizer.py`, `News.save`/`BlogPost.save` очищают `content` и `excerpt`, `Page.save` — через общий хелпер, вывод страниц прежний (`tests/integration/test_pages_api.py` зелёный без правок).
- **Сброс ISR `/home`:** `apps/common/services/nextjs_revalidate.py` (перенос `_revalidate_nextjs` без изменения логики и логов), `pages/signals.py` зовёт фоновую функцию; сигнал брендов после commit сбрасывает `/home` на любом сохранении/удалении бренда, который был или стал избранным; условия сброса кэша featured API прежние.
- **Nginx и smoke:** `location /marketing/` в `default.conf` и `local.conf`, скрипты `check-manager-route.sh`/`release-has-manager-route.sh` принимают раздел вторым аргументом (`[a-z]+`, по умолчанию `manager`), `main.yml` и `deploy.yml` проверяют `/marketing/`. `.sh` — LF.
- **Тесты:** `tests/integration/test_marketing_section.py` (73 теста, AC1–AC13, AC16), `tests/unit/test_marketing_admin_site.py` (21), `tests/unit/test_html_sanitizer.py` (13), `tests/unit/test_nextjs_revalidate.py` (19), новые сценарии в тестах nginx и скриптов.
- **Разрешённые отклонения от «существующие тесты без правок» (решение 13):** ожидание `apps/products/tests/test_brand_model.py:93` — русский текст; `RevalidateNextjsTest` перенесён из `apps/pages/tests.py` в `tests/unit/test_nextjs_revalidate.py` с новым путём патча и логгером, проверки прежние. **Базовый класс сменён с `SimpleTestCase` на `TestCase`:** под `tests/` autouse-фикстура `clear_db_before_test` обращается к БД, а `SimpleTestCase` запросы к БД запрещает.
- **Отклонения от стори (с причиной):**
  1. *Белый список страниц.* Стори считала, что `meta` и `link` есть в страничном списке тегов. На деле их там не было — только ключи атрибутов; bleach удалял эти теги и у страниц. Перенос сделан байт в байт: `PAGE_HTML_TAGS = RICH_HTML_TAGS`, `PAGE_HTML_ATTRIBUTES` = общие + ключи `meta`/`link`. Unit-тест закрепляет это, а не «сохраняются страничным списком».
  2. *Корни витрины.* В выборку категорий главной добавлено `parent__is_active=True` — ровно круг `homepage_categories_q()` без `sort_order > 0`, как сказано в решении 14 (в Task 4 условие было перечислено без него).
  3. *Сброс `/home` при правке описания избранного бренда.* Решение 13 и шаг выката 4 требуют сброса при любом сохранении избранного бренда, а Task 4b описывала хелпер внутри веток сброса кэша API (описание в них не входит). Сделано по AC7 и шагу выката: `/home` сбрасывается при любом сохранении бренда, который был или стал избранным, кэш API — по прежним трём веткам; в одном `on_commit` сначала кэш API, затем Next.
  4. *Неверное имя раздела в `release-has-manager-route.sh`* — код 2 («решать вызывающему»), а не 1: иначе опечатка в `deploy.yml` выглядела бы как «релиз раньше раздела» и молча пропускала проверку.
  5. *Права «только просмотр» у категорий главной.* Родительский `HomepageCategoryAdmin.get_form` теряет аргумент `change`, поэтому при одном `view_homepagecategory` форма карточки сохраняет поля; Django всё равно выводит их только для чтения, POST отвечает 403. Родитель по стори не меняется — AC11 проверяет HTML (нет полей ввода) и 403.
- **Риск для Alex — `&` в анонсах.** bleach экранирует голые `&`, `<`, `>` в тексте. `excerpt` фронтенд выводит в карточках новостей и блога и в meta description как текст, поэтому анонс «Скидки & подарки» после сохранения покажется как «Скидки &amp; подарки». Стори требует очищать `excerpt` (решение 19), поэтому поведение оставлено; если такие анонсы встретятся — отдельная правка (например, `html.unescape` на выводе или очистка `excerpt` без экранирования).
- **Шаги выката для Alex** (из стори, без изменений): (1) ручных шагов в БД нет, деплой сам делает `nginx -t`/reload; (2) `curl -sI https://optisport.ru/marketing/` → 302 на `/marketing/login/?next=/marketing/`, 404 от Next — `docker compose exec nginx nginx -s reload`; (3) до заведения маркетологов пересохранить в `/admin/` 3 новости и 3 статьи и проверить их глазами — у трёх записей-документов пропадёт встроенный `<style>`; (4) сохранить описание любого избранного бренда — в логе backend `Next.js revalidation triggered for /home`, при `skipped`/`rejected: HTTP 401` сверить `FRONTEND_INTERNAL_URL` и `REVALIDATE_SECRET`; (5) завести маркетологов в `/admin/` (`is_staff=True`, группа «Маркетинг»).
- ✅ Resolved review finding [low]: R42.6-1 — тест миниатюр не проверял адрес картинки. Добавлен `TestProductChangelist::test_photo_src` (7 параметров): фото варианта важнее `base_images`; `/products/…` → `/media/products/…`; `/media/…`, `http://…`, `https://…` без изменений; `uploads/…` и `/uploads/…` → `/media/uploads/…`. Тест сверяет `src` всех миниатюр строки списка. Код приложения не менялся. Мутации `_product_photo_url` убиты все три: без префикса `/media` у `/products/…`, `base_images` важнее фото варианта, относительный путь без `/media/`.

### File List

Новые:
- `backend/apps/banners/marketing_admin.py`
- `backend/apps/common/marketing_admin.py`
- `backend/apps/common/services/nextjs_revalidate.py`
- `backend/apps/common/utils/html_sanitizer.py`
- `backend/apps/products/marketing_admin.py`
- `backend/templates/admin/marketing/index.html`
- `backend/tests/integration/test_marketing_section.py`
- `backend/tests/unit/test_html_sanitizer.py`
- `backend/tests/unit/test_marketing_admin_site.py`
- `backend/tests/unit/test_nextjs_revalidate.py`

Изменённые:
- `.github/workflows/deploy.yml`
- `.github/workflows/main.yml`
- `_bmad-output/implementation-artifacts/Story/42-6-marketing-section.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/apps/banners/apps.py`
- `backend/apps/common/admin.py`
- `backend/apps/common/apps.py`
- `backend/apps/common/models.py`
- `backend/apps/pages/models.py`
- `backend/apps/pages/signals.py`
- `backend/apps/pages/tests.py`
- `backend/apps/products/admin.py`
- `backend/apps/products/apps.py`
- `backend/apps/products/models.py`
- `backend/apps/products/signals.py`
- `backend/apps/products/tests/test_brand_model.py`
- `backend/freesport/admin_site.py`
- `backend/freesport/urls.py`
- `backend/tests/unit/test_check_manager_route_script.py`
- `backend/tests/unit/test_nginx_security_headers.py`
- `backend/tests/unit/test_release_has_manager_route_script.py`
- `docker/nginx/conf.d/default.conf`
- `docker/nginx/conf.d/local.conf`
- `docker/nginx/snippets/app-headers.conf`
- `scripts/deploy/check-manager-route.sh`
- `scripts/deploy/release-has-manager-route.sh`

### Change Log

- 2026-10-16 — стори создана (`bmad-create-story`), статус `ready-for-dev`.
- 2026-10-16 — ответы Alex: активность категории на главной — только чтение (решение 14, AC8, Task 4, таблица мутаций, «Подводные камни»; эпик FR-42-22 и `section-contents.md` поправлены); одновременная правка одного поля не критична (решение 11); рубрики в `/admin/` нужны (решение 7).
- 2026-10-16 — party mode, ответы Alex: + решение 19 и AC16 (очистка HTML новостей и блога на бэкенде, общий хелпер с `Page`, Task 4a, шаг выката 3); решение 12 — категория без `__str__`, `CategoryPathListFilter` (прод: 121 категория, глубина до 5); решение 13 — подсказка «в течение часа» у флага бренда (ISR главной 3600 с); решение 14 — исключение для readonly `parent` записано явно, `select_related("parent")`; AC4, AC7, AC13, таблица мутаций, Dev Notes обновлены.
- 2026-10-16 — party mode, Alex выбрал вариант «а»: подсказка «в течение часа» заменена сбросом ISR `/home` сигналом брендов (решение 13, AC7, Task 4b). Сброс `_revalidate_nextjs` переезжает из `pages` в `apps/common/services/nextjs_revalidate.py`, тесты переносятся с прежними проверками. Шаг выката 4 — проверка по логу (механизм на проде за 30 дней ни разу не сработал). Баннеры, новости и блог проверены на проде: обновляются сразу, изменений не требуют.
- 2026-10-16 — реализация (`bmad-dev-story`) на `feature/42-6-marketing-section`: сайт `/marketing/` с семью моделями, белые списки товаров/брендов/категорий главной, рубрики с защитой удаления, плашка подписчиков, санитайзер HTML новостей и блога, сброс ISR `/home` сигналом брендов, nginx и smoke-проверки `/marketing/`. 126 тестов в четырёх новых файлах (из них 5 перенесены), 27/27 мутаций убиты; полный прогон 4458 passed, 76 skipped, 0 failed; black/isort/flake8/mypy чистые, миграций нет. Статус `review`.
- 2026-10-16 — исправление по ревью (`bmad-dev-story`): закрыто R42.6-1 — тест `src` миниатюр списка товаров (7 случаев, 3/3 мутации убиты). Полный прогон 4465 passed, 76 skipped, 0 failed; black/isort/flake8 чистые. Статус `review`.
