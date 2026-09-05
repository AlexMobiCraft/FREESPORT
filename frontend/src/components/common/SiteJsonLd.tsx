/**
 * Разметка schema.org уровня сайта: Organization + WebSite (Story 41.6).
 *
 * Оба узла лежат в одном `@graph`, а не в двух отдельных `<script>`: только так
 * `WebSite.publisher` ссылается на `Organization` по `@id`, и робот видит
 * связанные сущности, а не две карточки рядом.
 *
 * Монтируется в корневом layout — он единственный покрывает и `(blue)`, и
 * `(electric)`, и `(coming-soon)`. Осознанное следствие: блок попадает и на
 * `not-found.tsx`; страница 404 уже несёт `noindex`, разметка на ней инертна.
 *
 * `dangerouslySetInnerHTML` здесь безопасен: данные — статические константы
 * модуля, пользовательского ввода нет. Появится динамика — потребуется
 * экранирование `<` в `<`.
 */

import { ORGANIZATION_JSON_LD, WEBSITE_JSON_LD } from '@/config/organization';

const SITE_GRAPH = {
  '@context': 'https://schema.org',
  '@graph': [ORGANIZATION_JSON_LD, WEBSITE_JSON_LD],
};

export function SiteJsonLd() {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(SITE_GRAPH) }}
    />
  );
}
