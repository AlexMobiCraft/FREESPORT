Step Id: 59

# Технический долг и несоответствия документации (FREESPORT)

Дата: 2026-01-18

### 📋 Список выявленных проблем

1.  **Противоречие в командах импорта 1С:**
    - **Где:** `docs/architecture/20-1c-integration.md` vs `docs/architecture/import-architecture.md`.
    - **Суть:** В одном месте предлагаются команды `import_catalog_from_1c`/`import_offers_from_1c`, в другом используется реализованная `import_products_from_1c`.
    - **Рекомендация:** Стандартизировать документацию под `import_products_from_1c`.

2.  **Неактуальный индекс документации:**
    - **Где:** `docs/index.md`.
    - **Суть:** Множество документов помечены как "To be generated", хотя они уже существуют в папке `docs/architecture/`.
    - **Рекомендация:** Обновить ссылки в `docs/index.md`.

3.  **Безопасность JWT: Stateless Access Tokens:**
    - **Где:** `backend/apps/users/views/authentication.py`.
    - **Суть:** Access токены не инвалидируются немедленно при выходе (действуют до 60 мин).
    - **Рекомендация:** Добавить Redis blacklist для access токенов или сократить TTL до 15-30 мин.

4.  **Безопасность JWT: Race Condition при ротации:**
    - **Где:** `frontend/src/services/api-client.ts`.
    - **Суть:** Одновременный refresh с разных устройств может привести к разлогину из-за `ROTATE_REFRESH_TOKENS=True`.
    - **Рекомендация:** Документировать поведение или рассмотреть sliding sessions.

5.  **Отсутствие функции "Выйти со всех устройств":**
    - **Где:** `backend`.
    - **Суть:** Нет endpoint для массовой инвалидации всех сессий пользователя.
    - **Рекомендация:** Реализовать endpoint `/auth/logout-all/` через очистку `OutstandingToken`.

6.  **Дублирование логики очистки сессии (Frontend):**
    - **Где:** `authStore.ts`, `api-client.ts`, `AuthProvider.tsx`.
    - **Суть:** Логика удаления токенов и очистки состояния дублируется в трех местах.
    - **Рекомендация:** Централизовать в общую функцию `clearAuthState()`.

7.  **Хардкод SITE_URL в Backend:**
    - **Где:** `apps/users/views/authentication.py` (Password Reset).
    - **Суть:** Используется `localhost:3000` в коде вместо `settings.SITE_URL`.
    - **Рекомендация:** Использовать значение из `settings`.

8.  **Middleware: Проверка токена без валидации:**
    - **Где:** `frontend/src/middleware.ts`.
    - **Суть:** Middleware проверяет только наличие cookie `refreshToken`, но не его валидность или срок действия.
    - **Рекомендация:** Добавить проверку JWT (без верификации подписи) на стороне Middleware для UX-улучшения.

9.  **Отсутствие атомарного "Переключения профиля":**
    - **Где:** `frontend/src/stores/authStore.ts`.
    - **Суть:** Нет метода для надежного переключения между аккаунтами без риска оставить старые токены валидными.
    - **Рекомендация:** Реализовать метод `switchAccount()`, обеспечивающий полную очистку старой сессии перед входом в новую.

10. **Безопасность: Cookies не HttpOnly:**
    - **Где:** `frontend/src/stores/authStore.ts`.
    - **Суть:** Cookies доступны через JavaScript, что повышает риск при XSS (хотя это нужно для Middleware).
    - **Рекомендация:** Исследовать возможность использования HttpOnly cookies с проксированием через Next.js API Routes или признать этот риск документированным.

11. **Логирование: console.error в Production:**
    - **Где:** `frontend/src/stores/authStore.ts:106`.
    - **Суть:** Ошибки логаута выводятся напрямую в консоль браузера.
    - **Рекомендация:** Подключить сервис сбора ошибок (Sentry или аналоги) и убрать прямые вызовы `console.error`.

12. **Дублирование логики проверки B2B-ролей (Низкая важность):**
    - **Где:** `frontend/src/components/product/ProductInfo.tsx`, `frontend/src/components/product/ProductSummary.tsx`.
    - **Суть:** Логика `['wholesale_level1', 'wholesale_level2', 'wholesale_level3', 'trainer', 'admin'].includes(userRole)` повторяется в нескольких файлах.
    - **Влияние:** Потенциальная проблема поддержки: при добавлении новой роли придётся обновлять логику в нескольких местах.
    - **Рекомендация:** Вынести в общую утилиту, например `canSeeRrp(userRole)` в `utils/pricing.ts`.

13. **1C Integration: Temp File Cleanup (Garbage Collection):**
    - **Где:** `backend/apps/products/management/commands/cleanup_1c_temp.py` (To be created).
    - **Суть:** Временные файлы в `MEDIA_ROOT/1c_temp/` после завершения импорта или при ошибке остаются на диске. Это может привести к переполнению хранилища.
    - **Рекомендация:** Реализовать management command `cleanup_1c_temp`, который удаляет файлы старше 24 часов (TTL). Запустить через Celery Beat.

14. **1C Import Protocol: Strict Session Creation:**
    - **Где:** `backend/apps/integrations/onec_exchange/views.py`.
    - **Суть:** Нарушение строгой семантики протокола обмена. Сейчас сессия создаётся "лениво" (при `import` или `complete`), вместо строгого создания при `mode=init`. Это приводит к проблемам с пустыми сессиями и требует workaround'ов.
    - **Рекомендация:** Переписать логику `ICExchangeView`: создавать сессию строго в `handle_init`, а в остальных методах (`file`, `import`, `complete`) только использовать существующую или возвращать ошибку, если сессии нет.

15. **1C Import Security: Public Media Root Exposure:**
    - **Где:** `backend/apps/integrations/onec_exchange/import_orchestrator.py`.
    - **Суть:** Файлы импорта сохраняются в `ImportOrchestratorService.import_dir = settings.MEDIA_ROOT / "1c_import"`. `MEDIA_ROOT`, как правило, доступен через Nginx как статика. Это значит, что любой может скачать ваши файлы импорта (цены, остатки, клиенты), просто подобрав URL.
    - **Рекомендация:** Немедленно перенесите хранение файлов импорта в приватную директорию `var/` или другую защищенную локацию за пределами web-root.

16. **Несоответствие логики/данных (Стоимость доставки):**
    - **Где:** `OrderExportService`.
    - **Суть:** Сервис устанавливает сумму документа XML равной `order.total_amount` (которая включает доставку), но список `<Товары>` содержит только физические товары. Если `delivery_cost > 0`, сумма строк не совпадет с суммой документа. Интеграция с 1С упадет при валидации.
    - **Рекомендация:** Добавить виртуальную позицию "Доставка" в список товаров, если стоимость доставки > 0.
