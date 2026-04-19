---
title: 'Мобильные изображения для маркетинговых баннеров'
slug: 'mobile-marketing-banner-images'
created: '2026-03-01'
status: 'done'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Django 5.2.7', 'DRF 3.14', 'PostgreSQL 15', 'Next.js 15', 'React 19', 'Tailwind CSS 4', 'Embla Carousel']
files_to_modify: ['backend/apps/banners/models.py', 'backend/apps/banners/serializers.py', 'backend/apps/banners/admin.py', 'backend/apps/banners/factories.py', 'backend/apps/banners/views.py', 'frontend/src/types/banners.ts', 'frontend/src/components/home/MarketingBannersSection.tsx']
code_patterns: ['cast() обёртки для полей модели', 'SerializerMethodField для URL изображений', 'fieldsets в Admin для группировки полей', 'нативный <picture>+<source>+<img> для responsive images', 'aspect-[21/9] md:aspect-[3/1] для responsive']
test_patterns: ['pytest + Factory Boy (backend)', 'Vitest + React Testing Library (frontend)', 'MSW для API mocking']
---

# Tech-Spec: Мобильные изображения для маркетинговых баннеров

**Created:** 2026-03-01

## Overview

### Problem Statement

Маркетинговые баннеры показывают одно и то же изображение на всех устройствах. На мобильных устройствах изображение обрезается или искажается из-за несовпадения пропорций, что ухудшает визуальное восприятие и эффективность баннеров.

### Solution

Добавить отдельное поле `mobile_image` в модель Banner для загрузки изображений с пропорциями 21:9, оптимизированных под мобильные устройства. На фронтенде использовать нативный HTML `<picture>` + `<source media>` для загрузки мобильного изображения без JS и без проблем с SSR/hydration. При отсутствии мобильного изображения — fallback на десктопное.

### Scope

**In Scope:**
- Новое поле `mobile_image` в модели Banner (применяется только для type=marketing)
- Миграция БД
- Обновление сериализатора (новое поле `mobile_image_url`)
- Обновление Django Admin (загрузка мобильного изображения)
- Обновление OpenAPI примера в views.py
- Обновление `MarketingBannersSection` — `<picture>` + `<source>` для мобильного изображения
- Обновление типа `Banner` на фронтенде
- Обновление Factory Boy фабрик для тестов
- Fallback: если мобильное изображение не загружено — показывать десктопное

**Out of Scope:**
- Hero-баннеры
- Автоматическая обрезка/ресайз изображений
- Оптимизация изображений (WebP конвертация и т.д.)
- Валидация размера/формата загружаемого изображения

## Context for Development

### Codebase Patterns

- Модель Banner в `backend/apps/banners/models.py` использует `cast()` обёртки для всех полей
- Изображения загружаются через `ImageField` с `upload_to="promos/%Y/%m/"` и `blank=True`
- Сериализатор `BannerSerializer` использует `SerializerMethodField` для `image_url`, возвращает `obj.image.url` (относительный путь — безопасно, т.к. всегда `/media/...`)
- Кеш инвалидируется через Django signals (`post_save`, `post_delete`) в `signals.py`
- Admin использует `fieldsets` для группировки полей, есть `image_preview` метод. Превью использует `format_html()` (безопасно — экранирует аргументы, НЕ `mark_safe`)
- `views.py` содержит `@extend_schema` с `OpenApiExample` — хардкоженный пример ответа API
- Frontend `MarketingBannersSection` использует Embla Carousel через `useBannerCarousel` hook
- Компонент использует `aspect-[21/9] md:aspect-[3/1]` — на мобилке 21:9, на десктопе 3:1
- Изображения через Next.js `Image` с `fill` + `object-cover` + `sizes="(max-width: 768px) 100vw, 1280px"`
- Тип `Banner` в `frontend/src/types/banners.ts` — простой interface с `image_url: string`
- `BannerFactory` использует `generate_test_image()` для `image`, `type` по умолчанию HERO
- Существующие sub-factories не задают `type` — наследуют дефолт HERO. Все sub-factories автоматически унаследуют `mobile_image` от родителя
- Обработка ошибок загрузки изображений: `useState<Set<number>>` для `failedImages` + `handleImageError` callback — **используется `useState` а не `useRef`**, т.к. нужен ре-рендер для скрытия сломанных баннеров

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `backend/apps/banners/models.py` | Модель Banner — добавить поле `mobile_image` |
| `backend/apps/banners/serializers.py` | BannerSerializer — добавить `mobile_image_url` |
| `backend/apps/banners/admin.py` | BannerAdmin — добавить поле в fieldsets и превью |
| `backend/apps/banners/factories.py` | Factory Boy — добавить `mobile_image`, создать `MarketingBannerFactory` |
| `backend/apps/banners/views.py` | OpenAPI пример — добавить `mobile_image_url` в example |
| `frontend/src/types/banners.ts` | Тип Banner — добавить `mobile_image_url` |
| `frontend/src/components/home/MarketingBannersSection.tsx` | Компонент — `<picture>` для мобильного изображения |

### Technical Decisions

- Поле `mobile_image` опциональное (`blank=True`) — fallback на десктопное изображение
- Тот же `upload_to="promos/%Y/%m/"` что и у `image`
- Сериализатор возвращает `mobile_image_url` как `str` — всегда строку, никогда не `None`. Метод `get_mobile_image_url` явно возвращает `""` при отсутствии файла
- **Frontend: `<picture>` + `<source media>` вместо JS-подхода.** Отказ от `matchMedia` + `useState` в пользу нативного HTML `<picture>`. Причины:
  1. Нет hydration mismatch — SSR и клиент рендерят идентичный HTML
  2. Нет JS-зависимости — браузер сам выбирает изображение по media query
  3. Загружается ровно одно изображение — встроенное поведение `<picture>`
  4. Стандартное, проверенное решение без edge cases с state/callbacks
- **Отказ от Next.js `<Image>` в пользу нативного `<picture>`+`<img>` внутри баннера.** Next.js `<Image>` не поддерживает `<picture>` wrapper нативно. Для маркетинговых баннеров используем `<picture>` с `<img>` напрямую, с `loading="lazy"`. Стили через Tailwind CSS классы на `<img>`: `w-full h-full object-cover absolute inset-0`. **Security note:** переход на нативный `<img>` обходит `next/image` domain allowlisting, но это безопасно т.к. API возвращает только относительные пути (`/media/...`), контролируемые бэкендом
- **Обработка ошибки загрузки изображений.** Важно: `<picture>` НЕ делает автоматический fallback при HTTP-ошибке (404) `<source>`. Если media query совпадает и `<source srcSet>` возвращает 404, браузер НЕ переключается на `<img src>` — вызывается `onError`. Поэтому: `onError` на `<img>` внутри `<picture>` работает как финальный обработчик. При ошибке — `handleImageError(bannerId)` скрывает баннер через существующий `useState<Set<number>>` (`failedImages`). Отдельный fallback mobile→desktop при 404 не реализуется (out of scope — admin загружает рабочие изображения)
- Alt-текст: используется один `image_alt` для обоих изображений. Мобильное изображение — та же по смыслу картинка, но в других пропорциях, отдельный alt не нужен
- Кеш-инвалидация уже работает через signals — `post_save` срабатывает при любом изменении, включая только `mobile_image`
- **Поле `mobile_image` в модели глобальное (для всех типов).** На фронтенде используется только в `MarketingBannersSection`. Администратор может загрузить `mobile_image` для hero-баннера, но фронтенд его проигнорирует. Это intentional — упрощает модель и позволяет в будущем расширить на hero без миграции
- **Breakpoint alignment:** CSS `md:` (Tailwind) = `@media (min-width: 768px)`. `<source media="(max-width: 767px)">` = мобилка. На viewport 768px и шире — десктопное изображение с aspect 3:1. На viewport 767px и уже — мобильное изображение с aspect 21:9. Границы выровнены, пробела нет
- **Позиция `mobile_image` в модели:** добавляется после поля `image` и перед `image_alt` — логическая группировка: `image` → `mobile_image` → `image_alt`
- **Factory `mobile_image = ""`:** для Django `ImageField` с `blank=True` пустая строка `""` — корректное значение (а не `None`). `FieldFile.__bool__` проверяет `self.name`, пустая строка → `False`. Совпадает с проверкой `if obj.mobile_image:` в сериализаторе

## Implementation Plan

### Tasks

- [x] Task 1: Добавить поле `mobile_image` в модель Banner
  - File: `backend/apps/banners/models.py`
  - Action: Добавить **после поля `image`** (строка ~82) и **перед `image_alt`** (строка ~83):
    ```python
    mobile_image = cast(
        models.ImageField,
        models.ImageField(
            "Мобильное изображение",
            upload_to="promos/%Y/%m/",
            blank=True,
            help_text="Изображение для мобильных устройств (21:9, рекомендуемый размер: 1260×540px). Если не загружено — используется основное.",
        ),
    )
    ```
  - Notes: Следовать паттерну `cast()` как у существующего поля `image`. Поле опциональное, без валидации обязательности. Порядок полей: `image` → `mobile_image` → `image_alt` → `cta_text` → `cta_link`

- [x] Task 2: Создать миграцию БД
  - Action: Выполнить `python manage.py makemigrations banners`
  - Notes: Имя файла миграции генерируется автоматически Django. Не хардкодить номер

- [x] Task 3: Добавить `mobile_image_url` в сериализатор
  - File: `backend/apps/banners/serializers.py`
  - Action: Добавить `mobile_image_url = serializers.SerializerMethodField()` и метод:
    ```python
    def get_mobile_image_url(self, obj: Banner) -> str:
        if obj.mobile_image:
            return cast(str, obj.mobile_image.url)
        return ""
    ```
    Добавить `"mobile_image_url"` в `fields` и `read_only_fields` кортежи (после `"image_url"`)
  - Notes: Метод ВСЕГДА возвращает `str` (никогда `None`) — пустую строку при отсутствии файла

- [x] Task 4: Обновить Django Admin
  - File: `backend/apps/banners/admin.py`
  - Action:
    1. Обновить fieldset "Контент" — полный кортеж после изменения:
       ```python
       "fields": (
           "type",
           "title",
           "subtitle",
           "image",
           "image_preview",
           "mobile_image",
           "mobile_image_preview",
           "image_alt",
           "cta_text",
           "cta_link",
       ),
       ```
    2. Добавить метод:
       ```python
       @admin.display(description="Превью (мобильное)")
       def mobile_image_preview(self, obj: Banner) -> SafeString:
           """Превью мобильного изображения. Использует format_html() для экранирования."""
           if obj.mobile_image:
               return format_html(
                   '<img src="{}" style="max-width: 200px; max-height: 100px;" />',
                   obj.mobile_image.url,
               )
           return format_html('<span style="color: #999;">{}</span>', "Нет мобильного изображения")
       ```
    3. Добавить `"mobile_image_preview"` в `readonly_fields`

- [x] Task 5: Обновить Factory Boy фабрики
  - File: `backend/apps/banners/factories.py`
  - Action:
    1. В `BannerFactory` добавить `mobile_image = ""` (пустое по умолчанию). Django `ImageField` с `blank=True` хранит `""` при отсутствии файла. `FieldFile.__bool__` проверяет `self.name` → пустая строка = `False`. Совпадает с `if obj.mobile_image:` в сериализаторе
    2. Добавить новые фабрики:
    ```python
    class MarketingBannerFactory(BannerFactory):
        """Factory для маркетинговых баннеров"""
        type = Banner.BannerType.MARKETING
        image = factory.LazyFunction(generate_test_image)

    class MarketingBannerWithMobileImageFactory(MarketingBannerFactory):
        """Factory для маркетинговых баннеров с мобильным изображением"""
        mobile_image = factory.LazyFunction(generate_test_image)
    ```
  - Notes: Существующие sub-factories (`ActiveGuestBannerFactory` и др.) автоматически унаследуют `mobile_image = ""` от `BannerFactory` — дополнительных изменений не нужно

- [x] Task 6: Обновить OpenAPI пример в views.py
  - File: `backend/apps/banners/views.py`
  - Action: Добавить `"mobile_image_url": ""` в оба примера в `OpenApiExample.value` (строки 56-76). Для marketing примера можно указать `"mobile_image_url": "/media/promos/2025/01/wholesale_mobile.webp"`
  - Notes: Поддерживает консистентность документации API с реальным ответом сериализатора

- [x] Task 7: Обновить тип Banner на фронтенде
  - File: `frontend/src/types/banners.ts`
  - Action: Добавить `mobile_image_url: string;` в интерфейс `Banner` после `image_url`
  - Notes: Поле всегда строка (пустая строка если нет мобильного изображения). API гарантирует `str`, никогда `null`

- [x] Task 8: Обновить MarketingBannersSection — `<picture>` для мобильного изображения
  - File: `frontend/src/components/home/MarketingBannersSection.tsx`
  - Action:
    1. Заменить Next.js `<Image>` на нативный `<picture>` + `<img>` в обоих блоках рендера (с Link и без Link). Структура:
       ```tsx
       <picture>
         {banner.mobile_image_url && (
           <source
             media="(max-width: 767px)"
             srcSet={banner.mobile_image_url}
           />
         )}
         <img
           src={banner.image_url}
           alt={banner.image_alt || banner.title}
           loading="lazy"
           className="w-full h-full object-cover absolute inset-0"
           onError={() => handleImageError(banner.id)}
         />
       </picture>
       ```
    2. Если `mobile_image_url` пустая строка — `<source>` не рендерится, браузер показывает `<img src>` (десктопное) на всех viewport. Это автоматический fallback без JS
    3. **Обработка ошибок:** `onError` на `<img>` срабатывает если загруженное изображение вернуло ошибку (404, broken). `<picture>` НЕ делает auto-fallback с `<source>` на `<img>` при HTTP-ошибке — если мобильное изображение 404, `onError` скроет баннер целиком. Это приемлемо: admin загружает рабочие изображения, 404 — исключительная ситуация. Существующий `handleImageError` + `failedImages` (`useState<Set<number>>`) работает без изменений
    4. Убрать импорт `Image` из `next/image` если он больше не используется в этом компоненте. **Внимание:** проверить, что `Image` не используется в других местах файла (напр. skeleton). Если используется — оставить импорт
    5. Контейнер `<picture>` наследует `relative w-full aspect-[21/9] md:aspect-[3/1]` от родительского div. `<img>` внутри позиционируется абсолютно через `absolute inset-0 w-full h-full object-cover`
  - Notes:
    - Нет JS state для mobile detection — нет hydration mismatch
    - Браузер загружает ровно одно изображение на основании media query
    - `loading="lazy"` работает нативно на `<img>` внутри `<picture>`
    - `sizes` атрибут не нужен — у `<source>` и `<img>` по одному `srcSet`/`src` URL (без responsive variants)

### Acceptance Criteria

- [x] AC1: Given маркетинговый баннер с загруженным `mobile_image`, when API запрашивает `/api/v1/banners/?type=marketing`, then ответ содержит непустое поле `mobile_image_url` с относительным путём к изображению (тип `string`)
- [x] AC2: Given маркетинговый баннер без `mobile_image`, when API запрашивает `/api/v1/banners/?type=marketing`, then поле `mobile_image_url` в ответе — пустая строка `""` (не `null`)
- [x] AC3: Given маркетинговый баннер с непустым `mobile_image_url`, when компонент рендерится, then HTML содержит `<picture>` с `<source media="(max-width: 767px)" srcSet={mobile_image_url}>` и `<img src={image_url}>`
- [x] AC4: Given маркетинговый баннер с пустым `mobile_image_url`, when компонент рендерится, then HTML содержит `<picture>` без `<source>`, только `<img src={image_url}>` (fallback)
- [x] AC5: Given Django Admin, when администратор редактирует маркетинговый баннер, then видно поле для загрузки мобильного изображения с превью и help_text с рекомендуемым размером 1260×540px

## Additional Context

### Dependencies

- Нет внешних зависимостей. Все используемые инструменты уже в проекте (Django ImageField, нативные HTML `<picture>`/`<source>`, Tailwind CSS)

### Testing Strategy

**Backend (unit):**
- Тест модели: создание баннера с `mobile_image` и без него
- Тест сериализатора: проверка `mobile_image_url` в ответе — непустая строка при наличии файла, `""` при отсутствии (никогда `null`)
- Тест кеш-инвалидации: обновление **только** `mobile_image` (без других полей) инвалидирует кеш баннеров
- Тест фабрик: `BannerFactory()` — `bool(instance.mobile_image) == False`; `MarketingBannerWithMobileImageFactory()` — `bool(instance.mobile_image) == True`

**Frontend (unit):**
- Тест MarketingBannersSection: при непустом `mobile_image_url` — рендерится `<picture>` с `<source media="(max-width: 767px)">`
- Тест MarketingBannersSection: при пустом `mobile_image_url` — рендерится `<picture>` без `<source>`, только `<img>`
- Тест MarketingBannersSection: SSR рендер совпадает с клиентским (нет hydration mismatch) — `<picture>` рендерится одинаково на сервере и клиенте
- Тест обработки ошибки: при ошибке загрузки изображения — баннер скрывается (существующее поведение через `handleImageError` + `useState<Set>`)

**Manual:**
- Загрузить мобильное изображение 21:9 через Django Admin
- Проверить отображение на мобильном устройстве (DevTools responsive mode, viewport 375px) — отображается мобильное изображение
- Проверить на десктопе (viewport 1280px) — отображается десктопное изображение
- Проверить граничный breakpoint: viewport 767px — мобильное, 768px — десктопное
- Проверить fallback при отсутствии мобильного изображения — десктопное на всех viewport

### Notes

- Поле `mobile_image` добавляется в модель Banner глобально (для всех типов), но на фронтенде используется только в `MarketingBannersSection`. Администратор может загрузить `mobile_image` для hero-баннера — фронтенд его проигнорирует. Это intentional: упрощает модель и позволяет расширить на hero без миграции
- Рекомендуемый размер мобильного изображения: 1260×540px (21:9)
- Alt-текст: общий `image_alt` используется для обоих вариантов изображения — мобильное изображение по смыслу та же картинка, но в других пропорциях
- Переход с Next.js `<Image>` на нативный `<picture>` + `<img>` для маркетинговых баннеров. Потеря: автоматическая оптимизация Next.js (lazy placeholder blur, srcSet generation), domain allowlisting. Выигрыш: SSR-совместимость, один сетевой запрос, нет hydration issues. Security mitigated: API возвращает только относительные пути `/media/...`. Для маркетинговых баннеров (крупные изображения, загружаемые через Admin) это приемлемый trade-off
- `<picture>` НЕ делает auto-fallback при HTTP-ошибке (404) `<source>`. Если мобильное изображение вернёт 404 при совпадении media query — баннер скроется целиком через `onError`. Это приемлемо для admin-загружаемых изображений

## Review Notes

- Adversarial review completed
- Findings: 10 total, 6 fixed, 2 skipped (noise), 2 acknowledged (documented trade-offs)
- Resolution approach: auto-fix all real findings
- Fixed: F1 (migrate), F2 (23 unit tests), F3 (factory DRY), F4 (decoding=async), F6 (picture extract), F8 (line length)
- Tests: 163 total (140 existing + 23 new), all passing

