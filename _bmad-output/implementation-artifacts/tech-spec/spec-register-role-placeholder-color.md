---
title: 'Приглушённый плейсхолдер select «Тип аккаунта» на /register'
type: 'bugfix'
created: '2026-08-23'
status: 'done'
route: 'one-shot'
review_loop_iteration: 0
context: []
---

# Приглушённый плейсхолдер select «Тип аккаунта» на /register

## Intent

**Problem:** В форме регистрации надпись «Выберите тип аккаунта» в поле «Тип аккаунта» рисовалась обычным цветом текста — так же, как уже выбранное значение, — тогда как остальные информационные подсказки формы (placeholder «Иван» в поле «Имя») приглушены. Пользователю неочевидно, что роль ещё не выбрана.

**Approach:** Красить нативный `<select>` токеном `--color-neutral-500` (тот же, которым `Input` красит placeholder), пока `selectedRole` пуст, и переключать на `--color-text-primary` после выбора роли. Пунктам списка цвет задан явно, чтобы они не унаследовали приглушённый цвет у `<select>`. Попутно исправлено кольцо фокуса того же поля: оно ссылалось на несуществующий токен `--color-primary-500` и откатывалось к `currentcolor`, из-за чего вместе с приглушением текста стало бы почти невидимым.

## Suggested Review Order

- Точка входа: цвет `<select>` зависит от того, выбрана ли роль — тот же токен, что и placeholder в `Input`.
  [`RegisterForm.tsx:309`](../../frontend/src/components/auth/RegisterForm.tsx#L309)

- Кольцо фокуса переведено на объявленный токен: `--color-primary-500` в репозитории не существует, битый `var()` откатывал ring к `currentcolor`.
  [`RegisterForm.tsx:306`](../../frontend/src/components/auth/RegisterForm.tsx#L306)

- Пунктам списка цвет проставлен явно; в комментарии зафиксировано ограничение Safari / Android Chrome.
  [`RegisterForm.tsx:315`](../../frontend/src/components/auth/RegisterForm.tsx#L315)

- Эталон, по которому выравнивался цвет: placeholder текстовых полей.
  [`Input.tsx:85`](../../frontend/src/components/ui/Input/Input.tsx#L85)

- Значение токена — `#8f9bb3`.
  [`globals.css:41`](../../frontend/src/app/globals.css#L41)

- Регрессионный тест на переключение классов: без него откат правки прошёл бы молча.
  [`RegisterForm.test.tsx:849`](../../frontend/src/components/auth/__tests__/RegisterForm.test.tsx#L849)
