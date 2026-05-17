# ADR-011: Timing- и behavioral-side-channels на `/subscribe/` и `/unsubscribe/` — принятый риск

## Status

Accepted

## Date

2026-05-17

## Context

Серия security-story (`security-email-enumeration-hardening`, `security-subscribe-status-unification`) закрыла **HTTP-code-differential** на endpoint'ах рассылки: `/subscribe/` и `/unsubscribe/` теперь возвращают идентичный `200 OK` с идентичным телом независимо от того, существует ли email в базе подписчиков.

Code review (2026-05-17) зафиксировал, что за пределами HTTP-кода остаются два side-channel'а более низкого уровня:

1. **Timing side-channel.** Путь успеха выполняет записи в БД (`Newsletter`, `UserConsent`, `unsubscribe()`); путь already_subscribed / unknown email записей не делает. Разница во времени ответа измерима усреднением по выборке.
2. **Behavioral side-channel.** Запись `unsubscribed_at` и эффект повторной отписки на `/unsubscribe/` отличают реальный email от несуществующего на уровне состояния БД.

Возникает вопрос: заводить ли отдельную story на полное устранение этих каналов (constant-time response pattern, выравнивание путей выполнения).

## Decision

**Принимаем timing- и behavioral-side-channels на `/subscribe/` и `/unsubscribe/` как acceptable risk.** Отдельная story на их устранение не заводится.

Решение пересматривается, если появится внешний триггер (см. раздел «Когда пересмотреть»).

## Consequences

### Обоснование (почему риск приемлем)

| Фактор | HTTP-code-differential (закрыт) | Timing/behavioral side-channel (принятый риск) |
|---|---|---|
| Сложность эксплуатации | Тривиальная — 1 запрос, читается число | Высокая — нужна статистика по сотням/тысячам сэмплов на каждый email |
| Влияние throttle `30/min` | Не мешает (1 запрос = 1 ответ) | Критично мешает — сбор выборки растягивается, сетевой jitter доминирует над полезным сигналом |
| Надёжность сигнала | 100% | Шумная, требует контролируемой сети |

- Throttle `30/min` (`subscribe` и `unsubscribe` scope), бывший «дополнительным барьером» для HTTP-вектора, для timing-вектора выступает **основной защитой** — он делает сбор статистически значимой выборки непрактичным.
- **Behavioral-канал** (`unsubscribed_at`, состояние БД) не наблюдаем для внешнего анонимного атакующего без доступа к БД — это side-channel только в модели угроз «атакующий уже внутри периметра», которая для публичного маркетингового endpoint'а не является целевой.
- Полное закрытие требует constant-time response pattern (искусственная задержка / выравнивание путей выполнения), что добавляет латентность и сложность кода ради угрозы с низкой эксплуатируемостью.

### Негативные последствия

- Теоретически остаётся возможность enumeration через статистический timing-анализ для атакующего с контролируемой сетью и готовностью обойти throttle через пул IP. Принимается осознанно.
- Endpoint'ы рассылки **не дают гарантии constant-time**. Любой будущий код, для которого constant-time критичен, не должен опираться на эти endpoint'ы как на образец.

### Граница решения

ADR покрывает **только** timing/behavioral side-channels на `/subscribe/` и `/unsubscribe/`. HTTP-code-differential считается закрытым предшествующими story и под этот acceptable risk не подпадает.

### Когда пересмотреть

Создать отдельную story на response-time equalization, если:

- пентест или security-аудит зафиксирует этот вектор как actionable finding;
- появится комплаенс-требование (защита ПДн), явно требующее constant-time для endpoint'ов с проверкой существования email;
- модель угроз поднимется — например, endpoint начнёт обрабатывать чувствительные сегменты (федерации, верифицированные B2B-клиенты), где факт подписки сам по себе чувствителен.

## References

- Story `security-email-enumeration-hardening` — закрытие `409→200` и `404→200`
- Story `security-subscribe-status-unification` — закрытие `201 vs 200`
- `_bmad-output/implementation-artifacts/deferred-work.md` — раздел `code review of security-email-enumeration-hardening (2026-05-17)`
- `backend/apps/common/views.py` — endpoint'ы `subscribe` / `unsubscribe`
- `backend/apps/common/serializers.py:155` — `UnsubscribeSerializer` (запись `unsubscribed_at`)
