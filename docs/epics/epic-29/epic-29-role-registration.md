# Epic 29: Role-Based Registration & User Verification

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-12-11 | 1.0 | Initial Epic Draft | John (PM) |

---

## Change Management

> [!IMPORTANT]
> Этот эпик расширяет функциональность регистрации из **Epic 28: Authentication System**. Добавляется явный выбор роли при регистрации и процесс верификации для специальных ролей (Тренер, Оптовик, Федерация).

---

## Goals

Реализовать строгую систему ролевой регистрации, где:

- Пользователи выбирают роль при регистрации
- Розничные покупатели получают немедленный доступ
- Бизнес-партнеры (Тренеры, Оптовики, Федерации) проходят обязательную верификацию администратором
- Администраторы получают уведомления о новых заявках

## Epic Description

### Existing System Context

- **Текущий функционал:** Epic 28 реализовал базовую регистрацию (B2C и B2B). Модель `User` в `apps/users/models.py` уже содержит поле `role` с 7-ю ролями, но frontend пока не использует явный выбор.
- **Технологический стек:**
  - Backend: Django + DRF
  - Frontend: Next.js 15.5.7 + TypeScript
  - Async: Celery (для email)
- **Точки интеграции:**
  - API эндпоинты регистрации (`/api/auth/register`, `/api/auth/b2b-register`)
  - `authStore` (Frontend state management)
  - Email Service (Celery tasks)

### Enhancement Details

**Что добавляется:**

1. **Role Selector UI** в форме регистрации (4 опции):
   - Розничный покупатель (по умолчанию)
   - Тренер / Спортивный клуб
   - Оптовик
   - Представитель спортивной федерации

2. **Conditional Warnings**: При выборе не-розничной роли появляется предупреждение о необходимости верификации.

3. **Verification Status Backend Logic**:
   - Для розничного покупателя: `role='retail'`, `is_active=True` (полный доступ сразу)
   - Для остальных ролей: `role='trainer|wholesale_level1|federation_rep'`, новое поле `verification_status='pending'`, `is_active=False`

4. **Email Notifications**:
   - **Админу**: "Новая заявка на регистрацию от {role} - {company_name}"
   - **Пользователю**: "Ваша заявка принята, ожидайте подтверждения"

5. **Login Block**: Пользователи со статусом `pending` не могут получить JWT токен. Frontend показывает сообщение "Ваш аккаунт на проверке".

**Как интегрируется:**

- Frontend передает выбранную роль в API
- Backend проверяет роль и устанавливает соответствующий статус
- Celery асинхронно отправляет email
- Middleware/JWT login endpoint проверяет статус верификации

**Критерии успеха:**

- Розничные покупатели регистрируются и входят немедленно
- Бизнес-партнеры видят уведомление "На модерации" и не могут войти
- Админы получают email о новых заявках
- Админы могут активировать пользователей через Django Admin

---

## Stories

> [!NOTE]
> Stories переупорядочены для правильной последовательности зависимостей

### Story 29.1: Role Selection UI & Warnings

**As a** Guest User  
**I want** to select my role (Retail, Trainer, Wholesaler, Federation) during registration  
**so that** I can access the platform with correct privileges and pricing

**Scope:**

- Обновить компонент `RegisterForm` (или создать `RoleBasedRegisterForm`)
- Добавить поле выбора роли (4 опции)
- Добавить условный `InfoPanel` с предупреждением для не-розничных ролей
- UI должен следовать Design System из `docs/frontend/design-system.json`

**Acceptance Criteria:**

1. Поле "Роль" присутствует и имеет 4 опции
2. "Розничный покупатель" выбран по умолчанию
3. При выборе не-розничной роли появляется информационный блок:
   - "Вам потребуется заполнить дополнительные данные"
   - "Доступ к порталу будет открыт после проверки администратором"
   - "Вы получите уведомление на email"
4. Форма передает выбранную роль в backend API

**Testing:**

- Unit-тесты для компонента формы
- Проверка валидации роли
- Визуальное тестирование условных предупреждений

---

### Story 29.2: Backend Verification Logic & Access Control

**As a** System  
**I want** to put non-retail registrations into pending status and block their login  
**so that** only verified business partners can access the platform

**Scope:**

- Расширить модель `User` (добавить поле `verification_status` или использовать `is_active`)
- Обновить `RegisterView` для обработки роли:
  - Если `role='retail'` → `is_active=True`
  - Иначе → `verification_status='pending'`, `is_active=False` (или любой флаг блокировки)
- Обновить JWT Login endpoint для проверки статуса верификации
- Frontend: обрабатывать 403/специальную ошибку "Account pending verification"

**Acceptance Criteria:**

1. Розничный покупатель регистрируется → может сразу войти
2. Тренер/Оптовик/Федерация регистрируется → НЕ может войти
3. При попытке входа "pending" пользователь получает ошибку с кодом и сообщением
4. Frontend показывает сообщение "Ваша учетная запись находится на проверке"

**Technical Notes:**

- **ВАЖНО:** Использовать существующее поле `verification_status` из модели User (уже содержит choices: 'unverified', 'verified', 'pending')
- Для розничных покупателей: `role='retail'`, `is_active=True`, `verification_status='verified'`
- Для бизнес-партнеров: `role='trainer|wholesale_level1|federation_rep'`, `is_active=False`, `verification_status='pending'`
- Миграция данных НЕ требуется - поле уже существует в `apps/users/models.py:190-196`

**Testing:**

- Unit-тесты для регистрации с разными ролями
- Integration-тесты для блокировки входа pending пользователей

**REGRESSION TESTS (Epic 28):**

> [!IMPORTANT]
> Критически важно проверить, что изменения не ломают существующую функциональность Epic 28

- [ ] Retail registration через `/register` работает (redirect на `/`)
- [ ] Retail login работает (JWT токены получены корректно)
- [ ] Password reset flow работает для всех ролей
- [ ] B2B registration из Epic 28 продолжает работать
- [ ] Создать отдельный test suite: `tests/regression/test_epic_28_intact.py`

---

### Story 29.3: Email Server Configuration

> [!IMPORTANT]
> **BLOCKING DEPENDENCY:** Эта история должна быть завершена ПЕРЕД Story 29.4 (Email Notification System), так как Celery tasks требуют настроенного SMTP сервера.

**As a** Developer  
**I want** to configure email server settings  
**so that** the system can send notifications to admins and users

**Scope:**

- Настроить SMTP сервер для отправки email
- Обновить Django settings (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`)
- Создать `.env` переменные для production
- Настроить `settings.ADMINS` список
- Тестирование отправки email на dev и prod окружениях

**User Actions:**

> [!NOTE]
> Перед началом разработки, пользователь (или DevOps) должен создать SMTP аккаунт

1. **Выбрать SMTP provider:**
   - **Development:** Gmail (бесплатно, лимит 500 писем/день)
   - **Production:** Yandex Mail для домена freesport.ru (или альтернативы: SendGrid, Mailgun)

2. **Создать аккаунт и получить credentials:**
   - **Gmail App Password:**
     - Перейти: <https://support.google.com/accounts/answer/185833>
     - Включить 2-Step Verification для аккаунта
     - Создать App Password для "Mail"
     - Скопировать 16-значный пароль (без пробелов)

   - **Yandex Mail для домена:**
     - Перейти: <https://connect.yandex.ru/portal/admin>
     - Создать почтовый ящик для домена (например, `noreply@freesport.ru`)
     - Использовать обычный пароль или настроить App Password
     - SMTP параметры: `smtp.yandex.ru`, порт `587`, TLS

3. **Настроить .env файл:**

   ```bash
   # Development (Gmail)
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-dev-email@gmail.com
   EMAIL_HOST_PASSWORD=your-16-digit-app-password
   
   # Production (Yandex)
   EMAIL_HOST=smtp.yandex.ru
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=noreply@freesport.ru
   EMAIL_HOST_PASSWORD=your-yandex-password
   
   # Admin emails (через запятую)
   ADMIN_EMAILS=admin1@freesport.ru,admin2@freesport.ru
   ```

**Acceptance Criteria:**

1. В `settings/base.py` или `settings/production.py` настроены email параметры
2. Email credentials хранятся в `.env` файле (не в коде)
3. В development режиме используется Console Backend или Mailhog для тестирования
4. В production используется реальный SMTP (Yandex для freesport.ru или Gmail)
5. `settings.ADMINS` настроены через переменную окружения `ADMIN_EMAILS`
6. Тестовое письмо успешно отправляется и доставляется

**Technical Notes:**

- **Development:** использовать `django.core.mail.backends.console.EmailBackend` или Mailhog
- **Production:** настроить SMTP (рекомендуется Yandex для freesport.ru, Gmail для dev)
- Добавить в `.env.example`:

  ```text
  # === НАСТРОЙКИ EMAIL ===
  EMAIL_HOST=smtp.yandex.ru  # или smtp.gmail.com для dev
  EMAIL_PORT=587
  EMAIL_USE_TLS=True
  EMAIL_HOST_USER=noreply@freesport.ru
  EMAIL_HOST_PASSWORD=your-password
  DEFAULT_FROM_EMAIL=noreply@freesport.ru
  
  # Список email администраторов для уведомлений (через запятую)
  ADMIN_EMAILS=admin1@freesport.ru,admin2@freesport.ru
  ```

- Обновить `settings/production.py`:

  ```python
  # Parse ADMIN_EMAILS from environment
  ADMINS = [
      ('Admin', email.strip()) 
      for email in config('ADMIN_EMAILS', default='').split(',') 
      if email.strip()
  ]
  ```

**Testing:**

- Manual: отправить тестовое письмо через Django shell:

  ```python
  python manage.py shell
  >>> from django.core.mail import send_mail
  >>> send_mail(
  ...     'Test Email',
  ...     'This is a test message.',
  ...     'noreply@freesport.ru',
  ...     ['admin@freesport.ru'],
  ...     fail_silently=False,
  ... )
  ```

- Проверить доставку на реальный email
- Проверить логи Celery при отправке асинхронных писем (после Story 29.4)

---

### Story 29.4: Email Notification System

> [!IMPORTANT]
> **DEPENDENCY:** Требует завершения Story 29.3 (Email Server Configuration)

**As an** Administrator  
**I want** to receive an email when a new Partner registers  
**so that** I can review and approve their request

**As a** Business Partner  
**I want** to receive confirmation that my application was received  
**so that** I know my request is being processed

**Scope:**

- Создать Celery task: `send_admin_verification_email(user_id)`
- Создать Celery task: `send_user_pending_email(user_id)`
- Создать email templates:
  - `emails/admin_new_verification_request.html`
  - `emails/user_registration_pending.html`
- Интегрировать вызов задач в `RegisterView` (для не-розничных регистраций)

**Acceptance Criteria:**

1. После регистрации Тренера/Оптовика/Федерации:
   - Админ получает email с деталями заявки (ФИО, компания, роль, email, дата)
   - Пользователь получает email "Ваша заявка принята, ожидайте проверки"
2. Для розничных покупателей email НЕ отправляются (или отправляется стандартное приветствие)

**Technical Notes:**

- Использовать `settings.ADMINS` (настроено в Story 29.3) для получения списка email администраторов
- Email должны отправляться асинхронно через Celery
- Настроить retry логику для отказоустойчивости:

  ```python
  @shared_task(
      bind=True,
      max_retries=3,
      default_retry_delay=60,  # 1 минута
      autoretry_for=(SMTPException,),
      retry_backoff=True,
      retry_backoff_max=600,  # 10 минут
  )
  def send_admin_verification_email(self, user_id):
      # ...
  ```

**MONITORING:**

> [!NOTE]
> Критически важно мониторить доставку email для бизнес-процесса верификации

- [ ] **Celery task failure rate tracked:**
  - Логировать все failed tasks в Celery
  - Пример: `logger.error(f"Failed to send email for user {user_id}: {exc}")`

- [ ] **Email delivery success/failure logged:**
  - SUCCESS: `logger.info(f"Email sent successfully to {user.email}")`
  - FAILURE: `logger.error(f"Email delivery failed: {exception}")`
  - Сохранять метаданные: timestamp, recipient, template, retry attempt

- [ ] **Alert если pending verification queue > 10 за 24 часа:**
  - Tracking: считать Users с `verification_status='pending'` и `created_at` за последние 24ч
  - Alert threshold: если count > 10 → отправить warning админам
  - Реализация: опционально через Celery Beat periodic task

**Testing:**

- Unit-тесты для Celery tasks (mock email sending):

  ```python
  @patch('apps.users.tasks.send_mail')
  def test_send_admin_verification_email(self, mock_send_mail):
      user = UserFactory(role='wholesale_level1')
      send_admin_verification_email.apply(args=[user.id])
      mock_send_mail.assert_called_once()
  ```

- Integration-тесты для проверки вызова задач из RegisterView
- Manual verification: проверить получение email на тестовом почтовом сервере (Mailhog или real SMTP)
- Performance test: отправить 50 параллельных регистраций, проверить все emails доставлены

---

## Compatibility Requirements

- [x] Существующие API остаются обратно совместимыми (расширение `/register` endpoint)
- [x] Изменения схемы БД обратно совместимы (добавление поля `verification_status`)
- [x] UI следует существующей Design System
- [x] Влияние на производительность минимально (async email)

---

## Risk Mitigation

**Основной риск:** Розничные пользователи случайно выбирают бизнес-роль и блокируются.

**Снижение риска:**

- Розничный покупатель — **опция по умолчанию**
- Четкие предупреждения для не-розничных ролей
- В будущем: возможность для админов изменить роль пользователя без повторной регистрации

**План отката:**

- Убрать Role Selector из UI
- Backend продолжит работать с дефолтной ролью `retail`

---

## Definition of Done

- [ ] Розничная регистрация работает без изменений (немедленный доступ)
- [ ] Бизнес-регистрация блокирует вход до верификации
- [ ] Пользователи со статусом `pending` не могут войти
- [ ] Email отправляются админам и пользователям
- [ ] Unit и Integration тесты покрывают оба потока
- [ ] Документация обновлена (`README.md`, `GEMINI.md`)
- [ ] Нет регрессии в существующей функциональности регистрации
