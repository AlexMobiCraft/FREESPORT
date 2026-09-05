/**
 * Тест-страж соцпревью (стори 41.6, AC4/AC5/AC7).
 *
 * Размеры `og:image` объявляются константами в `utils/seo.ts`, а браузер и
 * робот читают их из файла. Сверять две константы между собой бессмысленно —
 * поэтому здесь разбирается заголовок самого `public/image.jpg`. Когда владелец
 * принесёт файл 1200×630, тест сразу скажет, если константы не поменяли.
 *
 * Вторая половина — про `og-image.jpg`. Файл назывался как соцпревью, а работал
 * как заглушка hero: его читали `HeroSection` и `ElectricHeroSection`, и простое
 * удаление дало бы битую картинку ровно в тот момент, когда API баннеров
 * недоступен. Стори переименовала его в `hero-fallback.jpg`; здесь закреплено,
 * что старое имя не вернулось ни файлом, ни ссылкой из кода.
 */

import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  DEFAULT_OG_IMAGE,
  DEFAULT_OG_IMAGE_HEIGHT,
  DEFAULT_OG_IMAGE_TYPE,
  DEFAULT_OG_IMAGE_WIDTH,
} from '@/utils/seo';

const SRC_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FRONTEND_DIR = path.resolve(SRC_DIR, '..');
const PUBLIC_DIR = path.join(FRONTEND_DIR, 'public');

/**
 * Разбирает габариты JPEG по маркеру SOF (0xFFC0…0xFFCF, кроме 0xC4/0xC8/0xCC).
 * Заголовок читается напрямую, чтобы не тянуть в тесты графическую зависимость.
 */
function readJpegSize(file: string): { width: number; height: number } {
  const data = fs.readFileSync(file);
  let offset = 2; // пропускаем SOI (0xFFD8)

  while (offset < data.length) {
    if (data[offset] !== 0xff) {
      offset += 1;
      continue;
    }

    const marker = data[offset + 1];

    // Маркеры без полезной нагрузки
    if (marker === 0xd8 || marker === 0xd9 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) {
      offset += 2;
      continue;
    }

    const segmentLength = data.readUInt16BE(offset + 2);
    const isStartOfFrame =
      marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc;

    if (isStartOfFrame) {
      return {
        height: data.readUInt16BE(offset + 5),
        width: data.readUInt16BE(offset + 7),
      };
    }

    offset += 2 + segmentLength;
  }

  throw new Error(`Не найден SOF-маркер JPEG в файле ${file}`);
}

/** Все файлы `src/`, кроме каталогов сборки */
function collectSourceFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name === '.next') continue;
      collectSourceFiles(full, acc);
    } else {
      acc.push(full);
    }
  }

  return acc;
}

describe('Соцпревью: константы совпадают с файлом', () => {
  it('размеры public/image.jpg равны объявленным в utils/seo.ts', () => {
    const { width, height } = readJpegSize(path.join(PUBLIC_DIR, 'image.jpg'));

    expect(width).toBe(DEFAULT_OG_IMAGE_WIDTH);
    expect(height).toBe(DEFAULT_OG_IMAGE_HEIGHT);
  });

  it('объявленный MIME-тип соответствует расширению файла', () => {
    expect(DEFAULT_OG_IMAGE.endsWith('.jpg')).toBe(true);
    expect(DEFAULT_OG_IMAGE_TYPE).toBe('image/jpeg');
  });

  it('файл соцпревью существует по объявленному пути', () => {
    expect(fs.existsSync(path.join(PUBLIC_DIR, DEFAULT_OG_IMAGE.replace(/^\//, '')))).toBe(true);
  });
});

describe('Заглушка hero: og-image.jpg не вернулся', () => {
  it('public/og-image.jpg отсутствует', () => {
    expect(fs.existsSync(path.join(PUBLIC_DIR, 'og-image.jpg'))).toBe(false);
  });

  it('public/hero-fallback.jpg существует', () => {
    expect(fs.existsSync(path.join(PUBLIC_DIR, 'hero-fallback.jpg'))).toBe(true);
  });

  it('в src/ нет ссылок на /og-image', () => {
    // Ищем именно путь к файлу: голая подстрока `og-image` даёт ложное
    // срабатывание на чужой фикстуре `blog-image.jpg` в тестах блога.
    const pattern = /(^|[^\w-])og-image/;
    const offenders = collectSourceFiles(SRC_DIR).filter(file => {
      if (file === fileURLToPath(import.meta.url)) return false;
      return pattern.test(fs.readFileSync(file, 'utf-8'));
    });

    expect(offenders.map(file => path.relative(FRONTEND_DIR, file))).toEqual([]);
  });
});
