---
title: 'Создание и смена паролей пользователей в админке'
type: 'feature'
created: '2026-10-06'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** В Django-админке нельзя задать или сменить пароль существующему пользователю: `UserAdmin.fieldsets` в `backend/apps/users/admin.py` переопределены без поля `password`, поэтому в карточке нет кнопки «Задать пароль» / «Сбросить пароль». Встроенная форма `BaseUserAdmin.user_change_password` (`/admin/users/user/<id>/password/`) существует, но до неё не дойти из интерфейса. Создание пользователя с паролем уже работает (`password1`/`password2` в `add_fieldsets`), но это никак не проверено тестами.

**Approach:** Вернуть поле `password` (`ReadOnlyPasswordHashField` из `UserChangeForm`) в секцию «Основная информация» карточки пользователя — Django сам выводит хеш и кнопку на стандартную форму смены пароля. Покрыть интеграционными тестами весь сценарий: создание с паролем, кнопка в карточке, смена пароля и задание пароля записи без пароля (импорт 1С хранит `password=""`).

</frozen-after-approval>

## Implementation Notes

- Своих форм не добавляем: `AdminUserCreationForm` и `AdminPasswordChangeForm` в Django 5.2 уже валидируют пароли через `AUTH_PASSWORD_VALIDATORS` и пишут `LogEntry` («Пароль изменён»).
- После ревью: `UserAdmin.user_change_password` переопределён ради записи `AuditLog` (`action="change_password"`, IP, user-agent) — как у `block_users`/`approve`; `LogEntry` без IP и удаляем. Успех определяется по редиректу на карточку: ошибки формы отдают 200, «конфликт данных» редиректит на форму пароля.
- Имя маршрута формы пароля зашито в Django: `admin:auth_user_password_change`, не `users_user_...`.
- Пароль пользователю по email не отправляется: администратор передаёт его сам. Слать пароли открытым текстом нельзя.
- Ограничение «только суперпользователь меняет пароль суперпользователю» не вводим: сотрудник с правом `users.change_user` и так может поставить себе флаг `is_superuser` в той же карточке, отдельная проверка безопасности не добавит.
- Решение владельца (06.10.2026): задавать пароль непривязанной записи 1С разрешено без запрета и предупреждений. Побочный эффект: пароль, заданный записи 1С с ролью `unregistered`, исключает её из `User.objects.unlinked_1c_records()` — запись перестаёт быть кандидатом на привязку. Роль и статус менеджер выставляет сам. Публичный сброс пароля (`authentication.py:411`) такие записи по-прежнему пропускает.
- Файлы: `backend/apps/users/admin.py` (поле `password` в «Основной информации», `user_change_password`), `backend/tests/integration/test_admin_user_password.py` (новый, 8 тестов), `backend/tests/unit/test_users_admin.py`.

## Review Triage Log

- Пароль непривязанной записи 1С обходит защиту публичного сброса — medium, реально (`authentication.py:411`). HALT → владелец выбрал «разрешить молча», записано выше.
- Смена пароля не отзывает JWT — medium, реально, но дефект старый (сброс с сайта тоже не отзывает) → defer.
- Нет теста на сохранение карточки с полем `password` — false: поле `ReadOnlyPasswordHashField(disabled=True)`, форма подставляет initial; так же устроены fieldsets стандартного `UserAdmin` Django.
- Аудит только в `LogEntry`, без IP — medium, реально (правило модуля: критичные действия в `AuditLog`) → patch: `user_change_password` + проверки в тесте, включая `change_message`.
- Сотрудник с правом только просмотра видит кнопку, ведущую на 403 — low, реально, поведение стандартной админки Django; исправление требует своего виджета → отклонено.
- Тесты не проверяют подпись кнопки — low; текст переводит Django, проверка ссылки достаточна → отклонено.
- Нет AC/Verification в спеке — false: маршрут oneshot эти разделы удаляет по шаблону.
- Мелочи в тестах (`time_ns`, литерал старого пароля) — low, стиль соседнего `test_admin_link_1c_customer.py` → отклонено.
