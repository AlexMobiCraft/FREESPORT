/**
 * Тесты `buildMetadata` в части соцпревью (стори 41.6).
 *
 * Закрепляют ровно одно решение: размеры получает ТОЛЬКО картинка по умолчанию.
 * Габариты чужих изображений (обложка статьи, фото товара) нам неизвестны —
 * объявить их значило бы соврать роботу, поэтому чужой URL обязан остаться
 * голой строкой без `width`/`height`.
 *
 * Второе, что здесь защищено: `twitter.images` остаётся массивом строк. Twitter
 * размеров не читает, а объект вместо строки там ломает карточку.
 */

import { describe, it, expect } from 'vitest';

import {
  buildMetadata,
  DEFAULT_OG_IMAGE,
  DEFAULT_OG_IMAGE_HEIGHT,
  DEFAULT_OG_IMAGE_META,
  DEFAULT_OG_IMAGE_TYPE,
  DEFAULT_OG_IMAGE_WIDTH,
} from '../seo';

const base = {
  title: 'Заголовок',
  description: 'Описание',
  path: '/some-page',
};

describe('buildMetadata: соцпревью по умолчанию', () => {
  it('без параметра image подставляет картинку по умолчанию вместе с размерами', () => {
    const metadata = buildMetadata(base);

    expect(metadata.openGraph?.images).toEqual([DEFAULT_OG_IMAGE_META]);
  });

  it('при явном указании картинки по умолчанию строкой дополняет её размерами', () => {
    const metadata = buildMetadata({ ...base, image: DEFAULT_OG_IMAGE });

    expect(metadata.openGraph?.images).toEqual([DEFAULT_OG_IMAGE_META]);
  });

  it('сохраняет собственный alt, дополняя картинку по умолчанию размерами', () => {
    const metadata = buildMetadata({
      ...base,
      image: { url: DEFAULT_OG_IMAGE, alt: 'Свой альт' },
    });

    expect(metadata.openGraph?.images).toEqual([
      {
        url: DEFAULT_OG_IMAGE,
        width: DEFAULT_OG_IMAGE_WIDTH,
        height: DEFAULT_OG_IMAGE_HEIGHT,
        type: DEFAULT_OG_IMAGE_TYPE,
        alt: 'Свой альт',
      },
    ]);
  });

  it('константы описывают один и тот же файл', () => {
    expect(DEFAULT_OG_IMAGE_META).toMatchObject({
      url: DEFAULT_OG_IMAGE,
      width: DEFAULT_OG_IMAGE_WIDTH,
      height: DEFAULT_OG_IMAGE_HEIGHT,
      type: DEFAULT_OG_IMAGE_TYPE,
    });
  });
});

describe('buildMetadata: чужие картинки', () => {
  it('не приписывает размеры чужому URL, переданному строкой', () => {
    const metadata = buildMetadata({ ...base, image: 'http://example.com/article.jpg' });

    expect(metadata.openGraph?.images).toEqual(['http://example.com/article.jpg']);
  });

  it('не приписывает размеры чужому URL, переданному объектом', () => {
    const metadata = buildMetadata({
      ...base,
      image: { url: 'http://example.com/article.jpg', alt: 'Обложка статьи' },
    });

    expect(metadata.openGraph?.images).toEqual([
      { url: 'http://example.com/article.jpg', alt: 'Обложка статьи' },
    ]);
  });

  it('при image: null не отдаёт картинку вовсе', () => {
    const metadata = buildMetadata({ ...base, image: null });

    expect(metadata.openGraph?.images).toBeUndefined();
    expect(metadata.twitter?.images).toBeUndefined();
  });
});

describe('buildMetadata: twitter', () => {
  it('оставляет twitter.images массивом строк для картинки по умолчанию', () => {
    const metadata = buildMetadata(base);

    expect(metadata.twitter?.images).toEqual([DEFAULT_OG_IMAGE]);
  });

  it('оставляет twitter.images массивом строк для чужой картинки-объекта', () => {
    const metadata = buildMetadata({
      ...base,
      image: { url: 'http://example.com/article.jpg', alt: 'Обложка статьи' },
    });

    expect(metadata.twitter?.images).toEqual(['http://example.com/article.jpg']);
  });
});

describe('buildMetadata: неизменность прочего контракта', () => {
  it('не добавляет robots, пока не запрошен noIndex', () => {
    expect(buildMetadata(base).robots).toBeUndefined();
    expect(buildMetadata({ ...base, noIndex: true }).robots).toEqual({
      index: false,
      follow: false,
    });
  });

  it('сохраняет canonical и базовые поля openGraph', () => {
    const metadata = buildMetadata(base);

    expect(metadata.alternates?.canonical).toBe('/some-page');
    expect(metadata.openGraph).toMatchObject({
      title: 'Заголовок',
      description: 'Описание',
      url: '/some-page',
      type: 'website',
    });
  });
});
