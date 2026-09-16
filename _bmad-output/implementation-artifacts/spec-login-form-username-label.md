---
title: 'Лейбл поля логина: «Введите свое учетное имя»'
type: 'chore'
created: '2026-09-16'
status: 'done'
route: 'one-shot'
---

# Лейбл поля логина: «Введите свое учетное имя»

## Intent

**Problem:** На странице `/login` поле ввода подписано «Электронная почта» и в пустом состоянии показывает placeholder `user@example.com`. Заказчику нужна нейтральная подпись «Введите свое учетное имя» и пустое поле без подсказки.

**Approach:** Точечная правка `LoginForm`: заменён `label`, удалён атрибут `placeholder`. Селекторы `getByLabelText` в `LoginForm.test.tsx` обновлены под новый accessible name. Валидация (`loginSchema`, `type="email"`, `autoComplete="email"`) не менялась — поле по-прежнему принимает email.

## Suggested Review Order

- Новый лейбл и отсутствие placeholder — единственная точка изменения UI.
  [`LoginForm.tsx:103`](../../frontend/src/components/auth/LoginForm.tsx#L103)

- Селекторы тестов обновлены под новый accessible name (16 замен).
  [`LoginForm.test.tsx:41`](../../frontend/src/components/auth/__tests__/LoginForm.test.tsx#L41)

- Тот же селектор в хелпере `submitForm` — рендерит реальный LoginForm через LoginPage.
  [`page.test.tsx:62`](../../frontend/src/app/(blue)/(auth)/login/__tests__/page.test.tsx#L62)
