/**
 * Разметка schema.org уровня сайта (стори 41.6, AC6).
 *
 * Здесь закрепляются три вещи, которые легко потерять при правках:
 *  1. блок ровно один — вторая копия `@graph` на странице даёт роботу два
 *     конкурирующих описания одной организации;
 *  2. `WebSite.publisher` ссылается на `Organization` по `@id` — иначе узлы
 *     лежат рядом, но не связаны;
 *  3. `potentialAction`/`SearchAction` отсутствует — `/search` перечислен в
 *     `Disallow` robots.txt, и объявлять действие, ведущее в закрытый раздел,
 *     значит противоречить самим себе.
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

import { SiteJsonLd } from '../SiteJsonLd';
import { SUPPORT_EMAIL, SUPPORT_PHONE_DISPLAY } from '@/config/contacts';
import { ORGANIZATION_ID, WEBSITE_ID } from '@/config/organization';
import { SITE_NAME, SITE_URL } from '@/utils/seo';

/** Разбирает единственный ld+json-блок компонента */
function renderGraph() {
  const { container } = render(<SiteJsonLd />);
  const scripts = container.querySelectorAll('script[type="application/ld+json"]');

  expect(scripts).toHaveLength(1);

  const parsed = JSON.parse(scripts[0].textContent ?? '');
  const graph = parsed['@graph'] as Array<Record<string, unknown>>;

  return {
    parsed,
    graph,
    organization: graph.find(node => node['@type'] === 'Organization')!,
    website: graph.find(node => node['@type'] === 'WebSite')!,
  };
}

describe('SiteJsonLd', () => {
  it('отдаёт ровно один блок ld+json с корневым @graph', () => {
    const { parsed, graph } = renderGraph();

    expect(parsed['@context']).toBe('https://schema.org');
    expect(graph).toHaveLength(2);
  });

  it('содержит узлы Organization и WebSite', () => {
    const { organization, website } = renderGraph();

    expect(organization).toBeDefined();
    expect(website).toBeDefined();
  });
});

describe('SiteJsonLd: узел Organization', () => {
  it('описывает организацию обязательными полями', () => {
    const { organization } = renderGraph();

    expect(organization['@id']).toBe(ORGANIZATION_ID);
    expect(organization.name).toBe(SITE_NAME);
    expect(organization.url).toBe(SITE_URL);
    expect(organization.sameAs).toEqual(expect.arrayContaining([expect.any(String)]));
  });

  it('объявляет логотип с фактическими размерами файла', () => {
    const { organization } = renderGraph();

    expect(organization.logo).toEqual({
      '@type': 'ImageObject',
      url: `${SITE_URL}/LOGO_OPTIsport.png`,
      width: 1014,
      height: 101,
    });
  });

  it('берёт телефон и почту из config/contacts, а не из своей копии', () => {
    const { organization } = renderGraph();

    expect(organization.telephone).toBe(SUPPORT_PHONE_DISPLAY);
    expect(organization.email).toBe(SUPPORT_EMAIL);
  });

  it('содержит почтовый адрес со страной RU', () => {
    const { organization } = renderGraph();

    expect(organization.address).toMatchObject({
      '@type': 'PostalAddress',
      addressCountry: 'RU',
    });
  });
});

describe('SiteJsonLd: узел WebSite', () => {
  it('связан с организацией через publisher → @id', () => {
    const { website, organization } = renderGraph();

    expect(website['@id']).toBe(WEBSITE_ID);
    expect(website.publisher).toEqual({ '@id': organization['@id'] });
  });

  it('объявляет язык и адрес сайта', () => {
    const { website } = renderGraph();

    expect(website.name).toBe(SITE_NAME);
    expect(website.url).toBe(SITE_URL);
    expect(website.inLanguage).toBe('ru-RU');
  });

  it('не объявляет potentialAction — /search закрыт в robots.txt', () => {
    const { website } = renderGraph();

    expect(website.potentialAction).toBeUndefined();
  });
});

describe('SiteJsonLd: абсолютные URL', () => {
  it('строит все ссылки из SITE_URL, а не из захардкоженного домена', () => {
    const { container } = render(<SiteJsonLd />);
    const json = container.querySelector('script')?.textContent ?? '';

    for (const url of [ORGANIZATION_ID, WEBSITE_ID]) {
      expect(url.startsWith(SITE_URL)).toBe(true);
    }
    // Домен появляется в разметке только как часть SITE_URL
    const hardcoded = json.match(/https:\/\/optisport\.ru/g) ?? [];
    const fromSiteUrl = SITE_URL.startsWith('https://optisport.ru')
      ? (json.match(new RegExp(SITE_URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? []).length
      : 0;
    expect(hardcoded.length).toBe(fromSiteUrl);
  });
});

describe('SiteJsonLd: экранирование при сериализации', () => {
  it('не выпускает в разметку литеральный `<`, пришедший из окружения', async () => {
    // `SITE_URL` берётся из `NEXT_PUBLIC_APP_URL` — это значение окружения, а не
    // литеральная константа модуля. Литеральный `</script>` внутри инлайн-скрипта
    // закрывает тег, поэтому `<` уходит в разметку только как `\\u003c`.
    vi.resetModules();
    vi.stubEnv('NEXT_PUBLIC_APP_URL', 'https://x.test/</script><img src=x>');

    const { SiteJsonLd: Reloaded } = await import('../SiteJsonLd');
    const { container } = render(<Reloaded />);
    const script = container.querySelector('script[type="application/ld+json"]')!;
    const html = script.innerHTML;

    expect(html).not.toContain('<');
    expect(html).toContain('\\u003c');
    // Экранирование не должно ломать разбор: робот обязан прочитать тот же граф
    expect(JSON.parse(script.textContent ?? '')['@graph']).toHaveLength(2);

    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('оставляет разметку валидным JSON при обычных данных', () => {
    const { container } = render(<SiteJsonLd />);
    const script = container.querySelector('script[type="application/ld+json"]')!;

    expect(script.innerHTML).not.toContain('<');
    expect(() => JSON.parse(script.textContent ?? '')).not.toThrow();
  });
});
