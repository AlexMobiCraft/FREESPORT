# FREESPORT Platform

> API-First E-commerce платформа для B2B/B2C продаж спортивных товаров

## 📋 Описание проекта

FREESPORT - современная платформа электронной коммерции, объединяющая 5 торговых марок в единой экосистеме B2B/B2C продаж. Проект реализует полнофункциональный интернет-магазин с акцентом на оптовые продажи для тренеров, спортивных федераций и дистрибьюторов.

## 🏗️ Архитектура

- **Backend:** Django 4.2 LTS + Django REST Framework 3.14+
- **Frontend:** Next.js 14+ + TypeScript 5.0+
- **Database:** PostgreSQL 15+
- **Cache:** Redis 7.0+
- **Authentication:** JWT токены с refresh стратегией

## 📁 Структура проекта (Monorepo)

```
freesport/
├── backend/          # Django + DRF API
│   ├── apps/
│   │   ├── users/    # Пользователи и роли
│   │   ├── products/ # Каталог товаров
│   │   ├── orders/   # Система заказов
│   │   └── cart/     # Корзина покупок
│   ├── freesport/    # Django settings
│   └── requirements.txt
├── frontend/         # Next.js 14+ SPA
│   ├── src/
│   │   ├── app/      # App Router
│   │   ├── components/
│   │   ├── hooks/
│   │   └── services/
│   └── package.json
├── docs/            # Документация проекта
├── docker/          # Docker конфигурации  
├── .github/         # CI/CD workflows
└── scripts/         # Automation scripts
```

## 🚀 Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

### Установка

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd freesport

# 2. Настроить backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Настроить frontend
cd ../frontend
npm install

# 4. Запуск с Docker
cd ..
docker-compose up -d
```

## 🔐 Ролевая система

- **retail** - Розничный покупатель
- **wholesale_level1-3** - Оптовики (3 уровня ценообразования)
- **trainer** - Тренеры (специальные цены)
- **federation_rep** - Представители федераций

## 📚 Документация

- [Architecture](docs/architecture.md) - Архитектурная документация
- [User Stories](docs/stories/) - Epic 1 stories (1.1-1.9)
- [PRD](docs/PRD.md) - Product Requirements Document
- [API Specification](docs/api-spec.yaml) - OpenAPI 3.0.3 спецификация

## 🛠️ Разработка

### Git Workflow

- `main` - продакшен ветка (защищена)
- `develop` - основная ветка разработки (защищена)
- `feature/*` - ветки для новых функций
- `hotfix/*` - ветки для критических исправлений

### Commands

```bash
# Backend
cd backend
python manage.py runserver

# Frontend  
cd frontend
npm run dev

# Tests
# Backend (Django + pytest)
cd backend
source venv/bin/activate
pytest --verbose --cov=apps --cov-report=html

# Frontend (Next.js + Jest)
cd frontend
npm test
npm run test:coverage

# Docker
docker-compose up    # Вся платформа
```

## 📈 Progress Tracking

**Epic 1 (Недели 1-2):**
- [x] [Story 1.1:](docs/stories/1.1.git.md) Настройка Git ✅ ЗАВЕРШЕНА
- [x] [Story 1.2:](docs/stories/1.2.development.md) Среда разработки ✅ ЗАВЕРШЕНА
- [x] [Story 1.3:](docs/stories/1.3.django-structure.md) Структура Django ✅ ЗАВЕРШЕНА
- [x] [Story 1.4:](docs/stories/1.4.nextjs-structure.md) Структура Next.js ✅ ЗАВЕРШЕНА
- [x] [Story 1.5:](docs/stories/1.5.ci-cd.md) CI/CD инфраструктура ✅ ЗАВЕРШЕНА
- [x] [Story 1.6:](docs/stories/1.6.docker.md) Docker контейнеры ✅ ЗАВЕРШЕНА
- [x] [Story 1.7:](docs/stories/1.7.testing.md) Тестирование ✅ ЗАВЕРШЕНА
- [x] [Story 1.8:](docs/stories/1.8.database.md) База данных ✅ ЗАВЕРШЕНА
- [ ] [Story 1.9:](docs/stories/1.9.design-brief.md) Design brief

## 📞 Контакты

**Development Team:** FREESPORT Dev Team  
**Project Manager:** Владелец проекта  
**Timeline:** 28 недель (6 недель до демо)

---

*Создано с ❤️ для спортивного сообщества*