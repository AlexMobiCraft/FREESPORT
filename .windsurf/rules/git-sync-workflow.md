---
description: Порядок сохранения изменений в GitHub и синка develop -> main (solo-dev)
---

# Git workflow: develop как единственный гейт, main как зеркало

Проект ведёт один разработчик. Проверки CI проходят один раз — на PR в `develop`.
В `main` изменения попадают прямым fast-forward пушем, без PR и без повторных проверок.

## Защита веток (setup-branch-protection.sh)

- `develop`: обязателен PR (0 аппрувов) + 5 required-чеков — «Бэкенд: тесты»,
  «Фронтенд: тесты», «build (3.12)», «Контракт синхронен с кодом»,
  «Проверки качества кода».
- `main`: прямой push разрешён, PR и required-чеки сняты. Запрещены force-push
  и удаление ветки (enforce_admins = true — правила действуют и на владельца).

## Сохранение изменений

```bash
git checkout develop && git fetch origin && git reset --hard origin/develop
git checkout -b <type>/<name>        # feature/*, fix/*, docs/*, hotfix/*
# ... правки, коммит ...
git push -u origin <type>/<name>
gh pr create --base develop ...
gh pr merge <N> --merge              # только merge commit, НЕ squash/rebase
```

Squash/rebase-merge запрещены: они переписывают коммиты и разводят историю веток.

## Синк develop -> main (только по команде владельца)

```bash
git fetch origin
git log --oneline origin/main..origin/develop   # что уедет в main
git push origin origin/develop:refs/heads/main  # fast-forward
```

- Push всегда fast-forward: `main` не содержит коммитов вне `develop`, поэтому
  обратный sync `main -> develop` не нужен никогда. Если push отклонён как
  non-FF — в `main` попал чужой коммит, разобраться до продолжения.
- Этот же push запускает релизный пайплайн: сборку prod-образов в ghcr.io,
  `deploy.yml` (approval на environment `production`) и `sync-to-public.yml`.
- НЕ создавать PR `develop -> main`: merge-коммит на `main` сломает FF-схему
  и вернёт необходимость back-merge.
