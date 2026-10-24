---
title: 'Визуальный редактор с картинками для новостей, статей и страниц'
type: 'feature'
created: '2026-10-24'
status: 'done'
baseline_commit: '11e060e4bdf0dcb3414daac197633afab3b28070'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/.windsurf/rules/gitnexus.md'
  - '{project-root}/backend/docs/testing-standards.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Поле `content` у `News`, `BlogPost` и `Page` в админке — голый `textarea`, куда сотрудник вписывает HTML руками; вставить картинку внутрь текста нельзя. Это касается и документов-страниц (политика ПДн, оферта, реквизиты, согласие на рассылку).

**Approach:** По образцу редактора топика PROCONTENT (TipTap 3, вставка картинки кнопкой, из буфера и перетаскиванием, плейсхолдер на время загрузки) — виджет Django-админки на TipTap 3 для поля `content` трёх моделей и endpoint загрузки картинок в `MEDIA_ROOT`. Хранение не меняется: HTML в `TextField`, очистка bleach при `save()`.

## Boundaries & Constraints

**Always:**
- Виджет работает в каждом сайте, где зарегистрирована модель (`/admin/`, `/marketing/`), без правки `admin_site.py`; загрузка доступна только тому, у кого есть право add или change на эту модель в этом сайте.
- Тулбар: отмена/повтор, H2, H3, H4, жирный, курсив, подчёркнутый, зачёркнутый, маркированный и нумерованный список, цитата, ссылка, таблица (вставить, строка/столбец до-после, удалить), картинка, выравнивание выбранной картинки (влево/центр/вправо через класс `align-left|align-center|align-right`), кнопка «HTML» — переключение на исходный код в `textarea` и обратно.
- Вывод редактора — подмножество белого списка: для эталонного HTML редактора (все кнопки тулбара) `sanitize_rich_html(x) == x`. Нет `style` (таблица и `col` без `min-width`), нет `data-*`, у `img` только `src alt class`, ссылки только `http`, `https`, `mailto`, `/`-относительные.
- Картинка: JPEG, PNG, WEBP, GIF, до 10 МБ (проверка размера до Pillow); формат определяет Pillow с `formats=` из этих четырёх, расширение берётся из формата; больше 40 Мп — отказ, предупреждение о decompression bomb — отказ; `exif_transpose`, затем уменьшение длинной стороны до 1920 px; статичные картинки всегда перекодируются (EXIF и GPS уходят), анимированные GIF/WEBP/PNG сохраняются как есть, а анимированный файл с EXIF (байт-в-байт GPS ушёл бы на сайт) или с длинной стороной больше 1920 px (анимации не уменьшаются) — отказ; имя — UUID, путь `content/images/%Y/%m/`; в HTML — относительный `/media/...`.
- Пока идёт загрузка, отправка формы заблокирована; узел загрузки не попадает ни в `textarea`, ни в режим HTML; при ошибке он удаляется, текст ошибки показан у редактора.
- Без действия пользователя (ввод, вставка, перетаскивание, кнопка тулбара) редактор не меняет `textarea`: транзакции нормализации ProseMirror его не трогают. POST формы без правок даёт тот же `content`, что POST с обычным `textarea`.
- Бандл собирается командой из `frontend/`, результат коммитится в static бэкенда; CI проверяет, что он совпадает с исходником. Образу backend Node не нужен.

**Решения владельца (24.10.2026):**
- Страницы в этой задаче правятся там же, где сейчас, — в `/admin/` суперпользователем. Юридический раздел `/legal/` с ролью «Юристы» (доступ: суперпользователи, «Руководители», «Юристы») — следующая отдельная задача (deferred-work); виджет подключается к `PageAdmin`, а не к сайту, поэтому там заработает без доработок.
- Спецификация остаётся целиком, несмотря на объём больше 1600 токенов.

**Never:**
- Не менять схему БД, белый список санитайзера и права разделов эпика 42; не создавать раздел `/legal/` и роль «Юристы» в этой задаче.
- Не удалять файлы картинок (ни при удалении записи, ни при удалении из текста) — осиротевшие файлы вне scope.
- Не подключать CDN и не тянуть React в админку; не ставить CKEditor/TinyMCE.
- Не журналировать загрузки в `STAFF_ACTIONS`.
- `excerpt` и SEO-поля остаются обычными полями.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Загрузка ок | PNG 3000×2000, 4 МБ, есть change | 200 `{"url": "/media/content/images/2026/10/<uuid>.png"}`, файл 1920×1280 | N/A |
| Ориентация | JPEG с EXIF Orientation=6 и GPS | сохранён повёрнутым, без EXIF | N/A |
| Анимация | анимированный GIF 3 МБ | сохранён байт-в-байт, расширение `.gif` | N/A |
| Анимация с EXIF | анимированный WEBP с EXIF (GPS) | 400 `{"error": "..."}` с просьбой убрать метаданные | файл не сохраняется |
| Большая анимация | анимированный GIF 2400×1350 | 400 `{"error": "..."}` с просьбой уменьшить до 1920 px | файл не сохраняется |
| Не картинка / чужой формат | текст в `evil.png`, SVG, PSD | 400 `{"error": "..."}` | файл не сохраняется |
| Большой файл / бомба | 11 МБ; PNG 12000×12000 | 400 | файл не сохраняется |
| Нет права | POST маркетинга в upload `/admin/`; сотрудник без add/change на модель | 302 на логин / 403 | файл не сохраняется |
| GET на upload | — | 405 | — |
| Реквизиты (единственная таблица на проде) | `content` страницы `requisites`: `table`, `td`, `b`, `br`, `class` | таблица видна и редактируется; после правки текста таблица в HTML, `class` ячеек теряется (на сайте не используется) | — |
| Статья-документ | статья блога, сохранённая целым HTML (`html`, `head`, `article`, `div`) | после первой правки — только содержимое `body` без обёрток, `h1` → `h2` | — |
| Без правок | любая запись открыта и сохранена | `content` как при сохранении обычного `textarea` | — |
| Текст без HTML | новость на проде: Markdown/голый текст без единого `<`, абзацы через `\r\n\r\n` | в редакторе каждый блок между пустыми строками — абзац, одиночный перенос — `<br>`, `##` и `**` видны как текст; `textarea` не меняется до действия пользователя | — |
| Текст стёрт | в визуальном режиме удалено всё содержимое, форма сохранена | редактор пишет в `textarea` пустую строку (а не `<p></p>`) | обычная ошибка «Обязательное поле» Django |
| Режим HTML | правка кода и возврат в визуальный режим | правка видна; то, чего нет в схеме, отбрасывается — описано в подсказке у кнопки | — |

</frozen-after-approval>

## Code Map

- `backend/apps/common/admin.py:351,434` -- `NewsAdmin`, `BlogPostAdmin`; наследники `MarketingNewsAdmin`/`MarketingBlogPostAdmin` (`common/marketing_admin.py:29,33`) получат миксин сами. GitNexus impact: MEDIUM, 26 зависимостей через импорт модуля; тесты — `tests/unit/test_marketing_admin_site.py`, `tests/integration/test_marketing_section.py`, `tests/unit/test_supervisor_admin_site.py`.
- `backend/apps/pages/admin.py:10` -- `PageAdmin`, только `/admin/`.
- `backend/freesport/admin_site.py:222` -- образец `get_urls`: свои пути до `super().get_urls()` (catch-all `<path:object_id>/`).
- `backend/apps/common/utils/html_sanitizer.py:25-103` -- белый список; не менять.
- `backend/apps/common/models.py:843,961`, `backend/apps/pages/models.py:68-76` -- `save()` чистит `content` при любом сохранении.
- `backend/freesport/settings/production.py:58` -- `STATICFILES_STORAGE` игнорируется Django 5.2 (`STORAGES` не задан) → имена static без хеша, а nginx (`default.conf:111-114`) кэширует `/static/` `immutable` на год. Отсюда `?v=<хеш>` в `Media`.
- `frontend/src/app/(blue)/[slug]/page.tsx:105` -- готовые arbitrary-стили контента; `news/[slug]/page.tsx:120`, `blog/[slug]/page.tsx:129`, `privacy-policy/page.tsx:127` -- класс `prose` без плагина typography не действует.
- `frontend/vitest.config.mts:30` -- `include` только `src/**`.
- `/media/`: прод `docker/nginx/conf.d/default.conf:131`, `localhost:3000` — rewrite `frontend/next.config.ts:91`, `localhost:80` — `local.conf:21`; запретов на `content/` нет. CSP без `unsafe-eval` — TipTap его не требует. Ревалидация страниц `pages/signals.py:56` уже покрывает правку.
- Локальный static: том `backend_static`, `collectstatic` в `entrypoint_backend.sh:12` закомментирован; на проде — `deploy.yml:458`.
- PROCONTENT, образец: `src/features/editor/components/TiptapEditor.tsx:132-228` (paste/drop/плейсхолдер), `extensions/ImageUpload.ts`. Не переносить: дубль `Underline` при StarterKit 3, `setContent` на каждое изменение, санитайзер, молчащий на сервере.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/package.json` -- devDependencies с точными версиями: `@tiptap/core`, `@tiptap/pm`, `@tiptap/starter-kit`, `@tiptap/extension-image`, `@tiptap/extension-table` (в v3 включает row/cell/header), `esbuild`; скрипт `build:admin-editor` (minify, без sourcemap и баннеров с датой) -- воспроизводимая сборка.
- [x] `frontend/admin-editor/src/*.ts` -- редактор на `@tiptap/core`: монтирование на `textarea[data-rich-editor]` (снять `required`, проверку пустоты оставить серверу); значение без единого `<` — текст: экранировать, блоки между пустыми строками (`\r?\n` с пробелами) — `<p>`, одиночный перенос — `<br>`; StarterKit (Heading 2–4 с разбором `h1` как `h2`, Link с протоколами из белого списка); Image без `title`, с атрибутом выравнивания в `class`; Table с `renderHTML` без `style`; узел загрузки (blob-превью, вне сериализации); флаг действия пользователя для `onUpdate`; при `editor.isEmpty` в `textarea` пишется `""`; загрузка `fetch` + токен из `csrfmiddlewaretoken` формы; блокировка submit; режим HTML.
- [x] `frontend/admin-editor/__tests__/*.test.ts`, `frontend/vitest.config.mts` -- расширить `include`; vitest на ProseMirror (happy-dom): эталонный HTML редактора — все кнопки тулбара плюс неразрывный пробел, ссылка с `?a=1&b=2`, `alt` с кавычками, `<` и `&` в тексте, кириллица, эмодзи, ссылка с `target`/`rel` от Link (на них расходятся сериализаторы браузера и html5lib); круговой проход фикстуры реквизитов, статьи-документа и новости-Markdown (`\r\n`, `<` в тексте не встречается, `&` встречается); нормализация без действия не трогает `textarea`; успех/ошибка загрузки — прямым вызовом обработчиков paste/drop.
- [x] `backend/apps/common/static/common/rich_editor/rich-editor.{js,css}`, `.gitattributes` -- собранный бандл; для каталога `-text`.
- [x] `.github/workflows/frontend-ci.yml` -- шаг `npm run build:admin-editor` и `git diff --exit-code` по каталогу бандла.
- [x] `backend/apps/common/rich_editor.py` -- `RichEditorWidget` (`Media` с `?v=<sha256[:12]>` файла, `data-upload-url`); `RichContentAdminMixin`: `get_urls` с `upload-image/` до родительских, через `self.admin_site.admin_view`, `require_POST`, проверка `has_add_permission or has_change_permission`; `formfield_for_dbfield` для `content`, `reverse` с `self.admin_site.name`, `help_text` формы — «Текст с оформлением и картинками. Кнопка «HTML» показывает исходный код.» (у модели он говорит «HTML или Markdown»; меняется в форме, а не в модели, чтобы не было миграции); `save_content_image()` по правилам картинок.
- [x] `backend/apps/common/admin.py`, `backend/apps/pages/admin.py` -- миксин первым в MRO.
- [x] `backend/tests/unit/test_rich_editor_upload.py` -- матрица I/O (сотрудник без права — снять права с пользователя вручную, группа их даёт); эталонный HTML из фикстуры фронтенда проходит `sanitize_rich_html` без изменений; виджет и URL в формах обоих сайтов.
- [x] `frontend/src/app/globals.css`, `frontend/src/app/(blue)/{[slug],privacy-policy,news/[slug],blog/[slug]}/page.tsx` -- класс `rich-content` вместо `prose` и arbitrary-стилей: типографика из `[slug]/page.tsx:105` плюс цитата, `img.align-*` с обтеканием, clearfix, без float на ширине < 640 px.

**Acceptance Criteria:**
- Given суперпользователь в `/admin/pages/page/<id>/change/`, when он вставляет картинку из буфера в политику ПДн и сохраняет, then на `/privacy-policy` картинка видна, а файл лежит в `media/content/images/`.
- Given сотрудник маркетинга в `/marketing/common/news/add/`, when он перетаскивает JPEG в текст, выравнивает вправо и сохраняет, then на странице новости картинка справа с обтеканием, на мобильной ширине — во всю ширину.
- Given статья блога с заголовками, списками и цитатой, when она открыта на сайте, then заголовки, маркеры списков и цитата оформлены так же, как на `/[slug]`.
- Given новый бандл в релизе, when сотрудник открывает форму, then браузер грузит новую версию (другой `?v=`).

## Implementation Notes

## Spec Change Log

- 24.10.2026, party mode, правки утвердил владелец: анимированный файл с EXIF → 400 (Always и матрица; правка frozen-блока согласована); стёртый текст → `""` вместо `<p></p>` (матрица, задача редактора); в эталонную фикстуру добавлены символы, на которых расходятся сериализаторы; `help_text` поля `content` переопределён в форме; подсказка у кнопки «HTML» задана текстом (Design Notes); потеря `id` и `h5`/`h6` принята по данным прода (Design Notes).
- 24.10.2026, вторая правка владельца: текст без `<` открывается абзацами (матрица, задача редактора, фикстура); анимация с длинной стороной больше 1920 px → 400 (Always, матрица).

## Review Triage Log

Прогон 1 (24.10.2026), слои: blind-hunter (BH), edge-case-hunter (EC), verification-gap (VG), graph-impact (GI).

| # | Находка | Вердикт | Обоснование | Маршрут |
|---|---------|---------|-------------|---------|
| 1 | VG: точка входа `index.ts` (ветка `DOMContentLoaded`) не исполняется тестами | medium | `{{ media }}` в `change_form.html` стоит в `extrahead` → скрипт в `<head>`, на реальной странице монтирование идёт только через `DOMContentLoaded`; тесты импортируют `src/editor` | patch |
| 2 | VG, BH: кнопка «Картинка» и `change` скрытого `input[type=file]` без теста | medium | основной способ вставки; поиск по `__tests__` — только paste/drop | patch |
| 3 | VG: понижение `h1` при вставке HTML (`transformPastedHTML`) без теста | low | проверено только через `parseContent`; удаление строки не роняет тесты | patch |
| 4 | VG, BH: ICC-профиль, прозрачность палитры, CMYK в `_reencode` без тестов | medium | ветки `kept`/`icc_profile`/`convert("RGB")` не покрыты; регрессия искажает цвета на сайте | patch |
| 5 | EC, BH: redo после отмены загруженной картинки возвращает узел загрузки с отозванным `blob:` | medium | вставка узла идёт в историю, замена на `image` — с `addToHistory: false`; redo повторяет шаг с узлом загрузки, сериализатор его пропускает — картинка молча теряется | patch |
| 6 | EC, BH: анимация с XMP (GPS) сохраняется байт-в-байт | medium | `_reject_animation` смотрит только EXIF; Pillow кладёт XMP WebP/PNG/GIF в `info["xmp"]`; цель правила — координаты не уходят на сайт | patch |
| 7 | EC, BH: вставка из Word/сайта оставляет `img` с `src` `file:`/`cid:` и т.п. | low | `ContentImage.parseHTML` отсекает только `data:`/`blob:`; bleach срежет `src` у `file:` → пустой `<img>` в тексте. Внешние `https://` — спека не решает, оставлены | patch |
| 8 | BH: внутренние ссылки `/…` получают `target="_blank" rel="… nofollow"` | medium | умолчание Link (`link.ts:263`), закреплено эталоном для `/blog`; `nofollow` на внутренней перелинковке вредит SEO | patch |
| 9 | BH: гонка `?v=` и `collectstatic` при деплое | medium | `deploy.yml`: `up --force-recreate backend` → ~45 с → `collectstatic`; в окне новый `?v=` отдаёт старый файл с `immutable` на год | patch |
| 10 | EC, BH: файл с пустым `file.type` отклоняется на клиенте | low | `validateImageFile` требует MIME из списка; формат решает сервер — прямая правка условия | patch |
| 11 | EC, BH: 403 из-за устаревшего CSRF показан как «Нет права» | low | любой 403 → `MESSAGES.forbidden`; правка текста сообщения | patch |
| 12 | GI, VG: класс `.rich-content` у `CmsPage` не закреплён тестом | low | у `/[slug]` нет render-теста, только метаданные; VG — `defer` | defer |
| 13 | GI: базовая линия циклов в `gitnexus.md` устарела (цикл `users/models.py ↔ staff_roles.py`) | low | цикл существовал до изменения; правка — файл правил агентов | defer |
| 14 | EC: `/\evil.com` проходит `isAllowedHref` | false | ссылки на любой внешний `https://` разрешены и так — границы безопасности нет | reject |
| 15 | EC: `#якорь`/`?q` превращаются в `https://#якорь` | low | редко (якоря схема не держит), фикс — новая ветка | reject |
| 16 | EC: `host:8080/x` без протокола принимается за схему | low | редко, фикс — новая ветка | reject |
| 17 | EC: Markdown с литеральным `<` разбирается как HTML | false | ровно правило frozen-матрицы «без единого `<`»; на проде `<` в новостях нет | reject |
| 18 | EC: сущности `&amp;` в голом тексте экранируются второй раз | low | на проде не наблюдалось, фикс — эвристика | reject |
| 19 | EC: зависший `fetch` навсегда блокирует сохранение | low | nginx/браузер обрывают запрос по таймауту; фикс — `AbortController` | reject |
| 20 | EC: осиротевшие файлы после отмены загрузки | false | Never: «не удалять файлы картинок… осиротевшие файлы вне scope» | reject |
| 21 | EC: вставка файла при выделенной картинке/ячейках заменяет выделение | false | стандартная семантика вставки поверх выделения | reject |
| 22 | EC: `destroy()` во время загрузки, `required` не возвращается | false | `destroy` в бандле не вызывается, только API для тестов | reject |
| 23 | EC: `<p><br></p>`/`<p>&nbsp;</p>` проходят обязательность | low | по спеке пусто = `editor.isEmpty`; визуально пустой абзац — редкость | reject |
| 24 | EC: битые кадры / байты после трейлера анимации | low | файл отдаётся как `image/*` по расширению из формата, не исполняется | reject |
| 25 | EC: маленькая картинка `align-*` растягивается на телефоне | false | AC: «на мобильной ширине — во всю ширину» | reject |
| 26 | BH: `code`/`codeBlock`/`hr` из StarterKit через input rules | low | `pre`, `code`, `hr`, `class` есть в белом списке — вывод проходит санитайзер; только оформление | reject |
| 27 | BH: нет поля `alt` в визуальном режиме | low | тулбар перечислен во frozen-intent исчерпывающе, `alt` правится в режиме HTML | reject |
| 28 | BH: сохранение из режима HTML обходит схему | false | подсказка говорит «при возврате в визуальный режим» — так и есть; bleach чистит при `save()` | reject |
| 29 | BH: палитровые картинки уменьшаются NEAREST | low | подтверждено (`PIL/Image.py:2293`), но палитровые картинки больше 1920 px редки, фикс — конвертация и квантизация | reject |
| 30 | BH: `label for` указывает на скрытый textarea | low | косметика доступности, фикс — новая связка | reject |
| 31 | BH: таблицы без `overflow-x` на телефоне; смена типографики старых постов | low / false | `display:block` ломает растяжение таблиц — не прямая правка; `prose` без плагина typography не действовал (Code Map) | reject |

## Design Notes

TipTap без React: `new Editor({ element, extensions, content: textarea.value, onUpdate })`; `onUpdate` пишет в `textarea` только при поднятом флаге действия пользователя. Миксин даёт URL на модель — `/marketing/common/news/upload-image/` и `/admin/common/news/upload-image/` — поэтому доступ решают тот же `admin_view` и `has_add_permission`/`has_change_permission` этого сайта, а не новая проверка ролей.

**Что схема редактора не держит.** У заголовков и абзацев нет `id`, заголовки только 2–4 уровня: после первой правки якоря `href="#..."` перестанут работать, `h5`/`h6` станут абзацами. Принято по данным прода на 24.10.2026: в 4 страницах, 4 новостях и 3 статьях нет ни `id`, ни ссылок `#`, ни `h5`/`h6`. Если юридический раздел заведёт оглавление с якорями, `id` придётся добавить в схему.

**Новости в Markdown.** На проде 24.10.2026 все 4 новости — Markdown или голый текст (`## **…**`, переносы `\r\n`), и сайт уже показывает `##` и `**` буквально одним абзацем. Разбор HTML схлопнул бы переносы при первой правке, поэтому текст без `<` открывается абзацами. Конвертации Markdown нет: после выката маркетолог убирает `##` и `**` в этих четырёх новостях кнопками тулбара.

**Подсказка у кнопки «HTML»:** «Правка исходного кода. При возврате в визуальный режим то, чего нет в тулбаре (div, span, стили, id, заголовки h1, h5, h6), будет удалено или упрощено».

## Verification

**Commands:**
- `cd frontend && npm run build:admin-editor && git diff --exit-code ../backend/apps/common/static/common/rich_editor/` -- бандл совпадает с исходником
- `cd frontend && npm run format:check && npm run lint && npx tsc --noEmit && npx vitest run admin-editor` -- зелёные, тесты редактора найдены
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q tests/unit/test_rich_editor_upload.py tests/unit/test_marketing_admin_site.py tests/unit/test_supervisor_admin_site.py tests/integration/test_marketing_section.py` -- зелёные
- секрет-греп `pre-merge-checks.yml:193` по бандлу -- без срабатываний

**Manual checks:**
- `docker compose --env-file .env -f docker/docker-compose.yml exec -T backend python manage.py collectstatic --noinput`, затем `http://localhost/admin/`: картинка в странице, новости и статье; реквизиты открываются с таблицей; без правок сохранение не меняет текст.
