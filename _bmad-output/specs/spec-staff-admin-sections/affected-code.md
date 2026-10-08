# Затрагиваемый код

Координаты сверены на `develop` @ `20ca0c31` (08.10.2026).

## Права и эскалация

| Место | Что сейчас | Что важно |
|---|---|---|
| `backend/apps/users/admin.py:236` `UserAdmin` | `fieldsets` с `is_staff`, `is_superuser`, `groups`, `user_permissions`; `filter_horizontal` по группам и правам | путь эскалации для любого с `change_user` |
| `backend/apps/users/admin.py:412` `actions` | `approve_b2b_users`, `reject_b2b_users`, `link_1c_customer`, `block_users`; разблокировки нет | действия пишут `AuditLog` |
| `backend/apps/users/admin.py:452` `user_change_password` | смена пароля пишет `AuditLog` `change_password` | переиспользовать для сброса пароля менеджером |
| `backend/apps/users/admin.py:520` `verify_b2b_view` | страница подтверждения B2B, проверяет `has_change_permission` | фильтр по региону нужен и здесь |
| `backend/apps/integrations/onec_exchange/permissions.py:11` | `is_staff` или `can_exchange_1c` | роли сотрудников с `is_staff` получают обмен 1С |
| `backend/apps/integrations/views.py:29` | `@staff_member_required` на запуске импорта | то же |
| `backend/apps/common/views.py:146,218,277,310` | `IsAdminUser` (= `is_staff`) на метриках синхронизации | то же |
| `backend/apps/products/views.py:515` | `include_inactive` для `is_staff` | сотрудник видит неактивные товары через API |
| `backend/freesport/urls.py:41,45` | `/admin/monitoring/`, `/admin/` | точки подключения новых разделов |
| `backend/templates/admin/index.html` | порядок блоков главной админки по `app_label` | шаблон главной для новых разделов |

## Регионы

| Место | Что сейчас |
|---|---|
| `backend/apps/common/models.py:1040` `ManagerRoutingRule` | `match_type` (`inn_region`, `country`, `fallback`), `match_value`, `manager_name`, `manager_email`, `federal_district`, `is_active`; ссылки на учётную запись нет |
| `backend/apps/users/services/region_routing.py:35` | страна вне России → правило по стране; иначе `tax_id[:2]` → правило по коду; пусто → `fallback` |
| `backend/apps/users/tasks.py:401` `send_manager_region_email` | письмо о регистрации по `resolve_manager_recipients` |
| `backend/apps/users/serializers.py:394,440`, `backend/apps/users/views/authentication.py:686` | точки постановки письма — там же нужно назначение ответственного |
| `backend/apps/users/models.py:233` `country`, `tax_id` | исходные данные региона |

## Конфликты с 1С

| Место | Что делает |
|---|---|
| `backend/apps/products/services/variant_import.py:1178` | перезаписывает `Product.description` непустым значением из 1С |
| `backend/apps/users/services/processor.py:618` | меняет `role` по виду цен соглашения при импорте контрагентов |
| `backend/apps/users/services/link_1c_customer.py:259`, `backend/apps/users/services/verify_b2b_application.py:222` | роль при привязке и при верификации |
| `backend/apps/orders/services/order_status_import.py:755,899` | статус заказа и мастер-заказа из 1С |
| `backend/apps/bonuses/signals.py:18` | `post_save` заказа → `accrue_for_order` при переходе в `accrual_status` |

## Модели и admin-классы разделов

| Раздел | Модель / admin |
|---|---|
| Клиенты | `users.User`, `CompanyInline`, `AddressInline` (`users/admin.py:48,83`) |
| Заказы | `orders.Order`, `OrderAdmin` (`orders/admin.py:38`), `export_to_csv` (`:187`) |
| Баннеры | `banners.Banner`, `BannerAdmin` (`banners/admin.py:18`) |
| Новости, блог | `common.News`, `common.BlogPost` (`common/admin.py:344,427`) |
| Рубрики | `common.Category` (`common/models.py:423`) — в админке не зарегистрирована |
| Товары | `products.Product`, `ProductAdmin` (`products/admin.py:373`), действия меток (`:507-561`), поля меток (`products/models.py:329-374`) |
| Бренды | `products.Brand`, `BrandAdmin` (`products/admin.py:84`), `is_featured` (`products/models.py:55`) |
| Категории на главной | `products.HomepageCategory` (`products/admin.py:325`) |
| Подписчики | `common.Newsletter` (`common/admin.py:272`) |
| Журнал | `common.AuditLog` (`common/models.py:315`), `AuditLog.log_action` |
| Уведомления | `common.NotificationRecipient` (`common/admin.py:526`) |
| Бонусы | `bonuses.BonusProgramSettings`, `BonusTransaction` (`bonuses/admin.py:27,120`) |
| Сводка | `CustomerSyncMonitor.get_business_metrics` (`common/services/customer_sync_monitor.py:154`) — метрики синхронизации, не продаж; для сводки руководителя годится частично |
