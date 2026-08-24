/**
 * Тест-страж: список известных маршрутов верхнего уровня в middleware обязан
 * покрывать фактическую структуру `src/app`.
 *
 * Без этой сверки новая страница верхнего уровня, добавленная в `app/`, но не
 * внесённая в `KNOWN_TOP_LEVEL_ROUTES`, начнёт молча отдавать 404: middleware
 * посчитает её несуществующим адресом.
 *
 * Обратное включение не проверяется — в списке есть `electric-orange`, который
 * живёт не в `app/`, а в `public/` и обслуживается rewrite из `next.config.ts`.
 */

import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { KNOWN_TOP_LEVEL_ROUTES } from '../middleware';

const APP_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'app');

/**
 * Собирает односегментные публичные маршруты App Router.
 *
 * Каталоги-группы `(name)` прозрачны для URL, динамические `[param]` и
 * служебные (`_`, `@`) пропускаются. Сегмент считается маршрутом, только если
 * содержит собственный `page.tsx`.
 */
function collectTopLevelRoutes(dir: string): Set<string> {
  const routes = new Set<string>();

  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;

    const name = entry.name;
    const full = path.join(dir, name);

    if (name.startsWith('(') && name.endsWith(')')) {
      // Группа маршрутов: её содержимое остаётся на том же уровне URL
      for (const nested of collectTopLevelRoutes(full)) routes.add(nested);
      continue;
    }

    if (name.startsWith('[') || name.startsWith('_') || name.startsWith('@')) continue;

    if (fs.existsSync(path.join(full, 'page.tsx'))) routes.add(name);
  }

  return routes;
}

describe('Список известных маршрутов верхнего уровня', () => {
  it('покрывает все односегментные страницы из src/app', () => {
    const actual = [...collectTopLevelRoutes(APP_DIR)].sort();
    const missing = actual.filter(route => !KNOWN_TOP_LEVEL_ROUTES.has(route));

    expect(missing).toEqual([]);
  });

  it('содержит electric-orange — rewrite на статику, а не страницу app/', () => {
    // Rewrites из next.config.ts выполняются ПОСЛЕ middleware, поэтому без
    // записи в списке рабочий адрес превратился бы в 404.
    expect(KNOWN_TOP_LEVEL_ROUTES.has('electric-orange')).toBe(true);
  });

  it('не содержит несуществующих маршрутов /product, /orders и /b2b-dashboard', () => {
    // У этих путей нет собственной страницы: /product существует только как
    // /product/[slug], а /orders и /b2b-dashboard перечислены в isProtectedRoute,
    // но страниц под них нет. Все три обязаны отдавать 404.
    expect(KNOWN_TOP_LEVEL_ROUTES.has('product')).toBe(false);
    expect(KNOWN_TOP_LEVEL_ROUTES.has('orders')).toBe(false);
    expect(KNOWN_TOP_LEVEL_ROUTES.has('b2b-dashboard')).toBe(false);
  });
});
