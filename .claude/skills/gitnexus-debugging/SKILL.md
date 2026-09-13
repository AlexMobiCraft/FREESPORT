---
name: gitnexus-debugging
description: "Use when the user is debugging a bug, tracing an error, or asking why something fails. Examples: \"Why is X failing?\", \"Where does this error come from?\", \"Trace this bug\""
---

# Отладка через GitNexus CLI

Команды — `npx gitnexus ...` в Bash, всегда с `-r "C:\Users\1\DEV\FREESPORT"` (индексов
FREESPORT два). Инструментов `gitnexus_*` и ресурсов `gitnexus://` нет — MCP отключён.
Справочник — `gitnexus-guide`.

## Когда использовать

- «Почему эта функция падает?», «Откуда эта ошибка?»
- Эндпоинт отдаёт 500, неожиданное поведение
- Регрессия после изменений

## Workflow

```
1. npx gitnexus status                                  → индекс свежий?
2. npx gitnexus query -r <repo> "<симптом или текст ошибки>" → связанные процессы и символы
3. npx gitnexus context -r <repo> <подозреваемый>        → вызывающие / вызываемые
4. npx gitnexus cypher -r <repo> "<цепочка или шаги>"     → трассировка, если нужна
5. Read исходников                                      → подтвердить корневую причину
```

> `stale` → попроси пользователя выполнить `! npx gitnexus analyze --skip-agents-md`.
> Граф показывает статические связи. Корневую причину подтверждай чтением кода, логами и тестами,
> а не только графом.

## Чеклист

```
- [ ] Понять симптом (текст ошибки, неверный результат)
- [ ] query по тексту ошибки или теме
- [ ] Выбрать подозреваемую функцию из processes / definitions
- [ ] context: кто её вызывает и что она вызывает
- [ ] Цепочка вызовов или шаги процесса через cypher
- [ ] Прочитать исходники, воспроизвести тестом
```

## Паттерны

| Симптом | Подход |
| --- | --- |
| Текст ошибки | `query` по тексту → `context` на месте, где бросается исключение |
| Неверное значение | `context` функции → пройти `outgoing` по потоку данных |
| Плавающий сбой | `context` → искать внешние вызовы (1С, YuKassa, CDEK), Celery, async |
| Медленно | `context` → символы с большим числом вызывающих (горячие пути) |
| Регрессия после правок | `detect-changes -s all` или `-s compare -b develop` |

## Цепочка вызовов

Синтаксис `[:CodeRelation {type: 'CALLS'}*1..2]` здесь не парсится — фильтр через `rels()`:

```bash
npx gitnexus cypher -r "C:\Users\1\DEV\FREESPORT" "MATCH p = (a)-[r:CodeRelation*1..2]->(b:Function {name: '_get_order_display_items'}) WHERE all(x IN rels(p) WHERE x.type = 'CALLS') RETURN properties(nodes(p), 'name') AS chain"
```

## Пример: «В письме о заказе нет позиций»

```
1. npx gitnexus query -r "C:\Users\1\DEV\FREESPORT" "email уведомления о заказе"
   → definitions: tasks.py (send_order_confirmation_to_customer, _build_order_email_text),
     signals.py (send_order_confirmation_email)
2. npx gitnexus context -r "C:\Users\1\DEV\FREESPORT" _get_order_display_items
   → incoming: _build_order_email_text, send_order_notification_email
3. Read backend/apps/orders/tasks.py и signals.py
   → письма уходят только для is_master=True, позиции собираются из sub_orders
4. Проверить, что у мастер-заказа есть sub_orders, — тестом
```
