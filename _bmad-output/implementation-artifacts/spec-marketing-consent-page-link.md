---
title: 'Страница «Согласие на получение рекламы» и ссылка на неё в чекбоксах рассылки'
type: 'feature'
created: '2026-09-21'
status: 'done'
baseline_commit: '68d168a0e6e8bc7084d402c1563d9c63d3e8ec92'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/spec-41-11-separate-subscribe-consents.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Чекбокс рассылки есть в четырёх формах: `RegisterForm`, `B2BRegisterForm`, `SubscribeForm`, `ElectricSubscribeForm`. Сейчас это одна фраза без полного текста согласия (ст. 18 38-ФЗ). Утверждённый полный текст длинный, в форму он не помещается.

**Approach:**
- Полный текст публикуется CMS-страницей `Page` со slug `marketing-consent`. Её отдаёт существующий маршрут `(blue)/[slug]`. Страница уже создана на проде вручную (`pages_page.id=4`, 2026-09-21), исходник — `tmp/marketing-consent.html`; кодом страница не создаётся.
- Чекбокс получает хвост со ссылкой на эту страницу, как у чекбокса ПДн.
- Под чекбоксом — мелкая строка про отписку.
- Изменённый текст оформляется новыми ревизиями реестра согласий.

## Boundaries & Constraints

**Always:**
- Текст чекбокса дословно: `Я даю согласие на получение информационных и рекламных рассылок от OPTISPORT по электронной почте на условиях «Согласия на получение рекламы»`.
- Кавычки-ёлочки со словами внутри — это `Link` на `/marketing-consent` с `target="_blank" rel="noopener noreferrer"`.
- Разметка повторяет чекбокс ПДн: `label` с префиксом плюс `Link`, у чекбокса `aria-labelledby="<prefix-id> <link-id>"`.
- Строка под чекбоксом: `Отписаться можно в любой момент по ссылке в письме.` (`text-body-xs text-text-secondary`). Она не входит в текст согласия и в реестр не попадает.
- Оператор в тексте согласия — ИП Семерюк (как в политике ПДн). Правки текста страницы — только через админку.
- Реестр `consent_texts.json`:
  - новые ревизии `2026-09-21-registration` в `registration_marketing_checkbox` и `2026-09-21-newsletter` в `newsletter_marketing_checkbox`, дописываются последними;
  - существующие ревизии не трогаются;
  - `known_versions` берётся из сообщения загрузчика.
- Обязательность чекбоксов не меняется: в регистрации необязателен, в подписке обязателен.
- Перед правкой символа — `npx gitnexus impact`. Прогоны pytest — последовательно.

**Ask First:** правка утверждённых текстов; изменение `Page`/API/`[slug]`; новые поверхности реестра.

**Never:** data-миграция страницы; отдельный маршрут `/marketing-consent` во фронтенде; раскрывающийся блок с полным текстом в форме; `required` вместо `aria-required`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Регистрация с согласием | `marketing_consent: true` + версия `2026-09-21-registration-…` | 201, запись `marketing_email` с новой версией | — |
| Регистрация со старой версией | `2026-09-17-registration-…` | `400 consent_text_outdated` | Форма просит обновить страницу |
| Подписка со старой версией | `2026-09-17-newsletter-…` | `400 consent_text_outdated` | То же |
| Клик по ссылке | — | Страница открывается в новой вкладке, галочка не меняется | — |

</frozen-after-approval>

## Code Map

- `backend/apps/common/consent_texts.json` -- реестр ревизий; версия = метка + хеш нормализованного текста
- `backend/apps/common/consent_texts.py` -- загрузчик; при расхождении `known_versions` печатает нужные строки
- `frontend/src/constants/consentTexts.ts` -- `CONSENT_TEXT_VERSIONS` (`registrationMarketing`, `newsletterMarketing`)
- `frontend/src/components/auth/RegisterForm.tsx`, `B2BRegisterForm.tsx` -- чекбокс рассылки (~стр. 497/546)
- `frontend/src/components/home/SubscribeForm.tsx`, `ElectricSubscribeForm.tsx` -- чекбокс рассылки; образец — чекбокс ПДн там же
- `frontend/src/__tests__/consent-texts-registry.test.tsx` -- страж: константы ↔ реестр ↔ отрисованный текст
- тесты четырёх форм в `__tests__/` рядом с ними; тесты реестра в `backend/apps/common/tests/`

## Tasks & Acceptance

**Execution:**
- [x] `backend/apps/common/consent_texts.json` -- добавить две ревизии, обновить `known_versions` по сообщению загрузчика, дополнить `description` поверхностей
- [x] `frontend/src/constants/consentTexts.ts` -- новые версии и комментарии
- [x] четыре формы -- префикс в `label`, `Link`, `aria-labelledby`, строка про отписку
- [x] тесты форм и стражей -- новые тексты и версии; проверить ссылку (`href`, `target`) и что клик по ней не ставит галочку
- [x] backend-тесты -- старые версии дают `consent_text_outdated`

**Acceptance Criteria:**
- Given любая из четырёх форм, when она отрисована, then доступное имя чекбокса рассылки совпадает с текстом его действующей ревизии в реестре.

## Design Notes

Выпуск: п. 7 текста обещает отписку в личном кабинете, этого пока нет. Синк в `main` — только вместе с задачей A (отписка в кабинете) или после неё.

## Verification

**Commands:**
- `cd docker && docker compose -p freesport-test -f docker-compose.test.yml run --rm -T backend pytest -q apps/common apps/users` -- expected: зелёный
- `cd frontend && npx vitest run src/components/auth src/components/home src/__tests__` -- expected: зелёный
- `cd frontend && npx tsc --noEmit && npx eslint src/components src/constants` -- expected: без ошибок

## Suggested Review Order

**Версии формулировки**

- Новые ревизии обеих поверхностей: текст с хвостом-ссылкой, разные метки
  [`consent_texts.json:63`](../../backend/apps/common/consent_texts.json#L63)

- Формы шлют новые версии — старые вкладки получат `consent_text_outdated`
  [`consentTexts.ts:42`](../../frontend/src/constants/consentTexts.ts#L42)

**Разметка чекбоксов**

- Образец: префикс в label, ссылка вне label, имя через aria-labelledby
  [`RegisterForm.tsx:493`](../../frontend/src/components/auth/RegisterForm.tsx#L493)

- То же в B2B-регистрации
  [`B2BRegisterForm.tsx:542`](../../frontend/src/components/auth/B2BRegisterForm.tsx#L542)

- Подписка: подсказка об отписке стоит под ошибкой
  [`SubscribeForm.tsx:301`](../../frontend/src/components/home/SubscribeForm.tsx#L301)

- Electric: ссылка и подсказка внутри span-подписи компонента
  [`ElectricSubscribeForm.tsx:390`](../../frontend/src/components/home/ElectricSubscribeForm.tsx#L390)

**Тесты и контракт**

- Прежняя формулировка регистрации отклоняется
  [`test_auth_registration_consent.py:440`](../../backend/tests/integration/test_auth_registration_consent.py#L440)

- Прежняя формулировка подписки отклоняется
  [`test_common_subscribe_api.py:540`](../../backend/tests/integration/test_common_subscribe_api.py#L540)

- Пример OpenAPI на действующей версии
  [`openapi.yaml:105`](../../docs/api/openapi.yaml#L105)
