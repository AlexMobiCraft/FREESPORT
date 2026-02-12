# Story: Маркетинговые баннеры на главной

**Статус**: Ready for Dev
**Приоритет**: High
**Оценка**: 5 Story Points

## Описание
Как маркетолог, я хочу иметь возможность управлять блоком дополнительных баннеров на главной странице под "Быстрыми ссылками", чтобы продвигать текущие акции и предложения.

## Контекст реализации
Вся техническая информация собрана в спецификации `tech-spec-marketing-banners.md` (файл будет переименован из `tech-spec-wip.md`).

### Основные компоненты
1. **Backend**:
   - Расширение модели `Banner` полем `type` (Hero/Marketing).
   - Фильтрация в API `ActiveBannersView` по типу.
   - Валидация типа в API.
2. **Frontend**:
   - Хук `useBannerCarousel` для общей логики.
   - Компонент `MarketingBannersSection`.
   - Обновление `HeroSection`.

## Acceptance Criteria

### AC1: Управление баннерами (Admin)
- [ ] В админке у модели Banner появилось поле "Тип" (Hero/Marketing).
- [ ] Можно создать баннер типа "Marketing".
- [ ] Можно отфильтровать список баннеров по типу в админке.

### AC2: API Фильтрация
- [ ] GET `/api/banners/?type=marketing` возвращает только маркетинговые баннеры.
- [ ] GET `/api/banners/?type=hero` возвращает только Hero баннеры.
- [ ] GET `/api/banners/?type=invalid` возвращает пустой список (или 400, согласно финальному решению в спеке).
- [ ] Если тип не указан, возвращаются Hero баннеры (обратная совместимость).

### AC3: Frontend Refactoring
- [ ] Логика карусели вынесена в `useBannerCarousel`.
- [ ] `HeroSection` использует этот хук и работает без визуальных изменений.

### AC4: Отображение Marketing Section
- [ ] Секция отображается под блоком Quick Links.
- [ ] Секция содержит заголовок, изображение, текст и кнопку (согласно дизайну/верстке).
- [ ] Работает автопрокрутка (через хук).
- [ ] При отсутствии активных баннеров секция не отображается.

## План работ (Tasks)
См. `tech-spec-task.md` для детального списка технических задач.

## Файлы для изменений
- `backend/apps/banners/models.py`
- `backend/apps/banners/views.py`
- `backend/apps/banners/admin.py`
- `frontend/src/services/bannersService.ts`
- `frontend/src/hooks/useBannerCarousel.ts`
- `frontend/src/components/home/HeroSection.tsx`
- `frontend/src/components/home/MarketingBannersSection.tsx`
- `frontend/src/components/home/HomePage.tsx`
