/**
 * Общие константы визуального редактора админки.
 *
 * Ограничения картинок повторяют серверные (`apps/common/rich_editor.py`):
 * проверка здесь только экономит сотруднику время на заведомо отклонённую загрузку,
 * решает всё равно сервер.
 */

export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'] as const;

export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;

export const IMAGE_ALIGNMENTS = ['left', 'center', 'right'] as const;

export type ImageAlignment = (typeof IMAGE_ALIGNMENTS)[number];

/** Атрибут узла загрузки: такой элемент не попадает ни в textarea, ни в режим HTML. */
export const UPLOAD_MARKER = 'data-rich-upload';

export const HTML_MODE_HINT =
  'Правка исходного кода. При возврате в визуальный режим то, чего нет в тулбаре ' +
  '(div, span, стили, id, заголовки h1, h5, h6), будет удалено или упрощено';

export const MESSAGES = {
  wrongType: 'Поддерживаются картинки JPEG, PNG, WEBP и GIF.',
  tooLarge: 'Картинка больше 10 МБ — уменьшите её и загрузите снова.',
  network: 'Нет связи с сервером, картинка не загружена. Попробуйте ещё раз.',
  session: 'Сессия истекла: войдите в админку заново и повторите загрузку.',
  // 403 даёт и устаревший CSRF-токен (повторный вход в другой вкладке).
  forbidden:
    'Нет права загружать картинки в этот раздел или страница устарела — обновите её и повторите.',
  failed: 'Не удалось загрузить картинку',
  waitForUpload: 'Дождитесь окончания загрузки картинки, затем сохраните.',
  badLink: 'Ссылка должна начинаться с https://, http://, mailto: или / (страница этого сайта).',
} as const;

/**
 * Ссылки, которые пропускает редактор: `http`, `https`, `mailto` и пути этого сайта.
 *
 * Белый список санитайзера на сервере шире, но редактор сам создаёт только эти
 * ссылки: `//host` — чужой сайт без протокола, `#якорь` схема не держит (у заголовков нет `id`).
 */
export function isAllowedHref(url: string | null | undefined): boolean {
  if (!url) {
    return false;
  }
  const value = url.trim();
  return isSitePath(value) || /^(?:https?:\/\/|mailto:)/i.test(value);
}

/** Путь этого сайта: `/…`, но не `//host` (чужой сайт без протокола). */
export function isSitePath(url: string | null | undefined): boolean {
  return /^\/(?!\/)/.test((url ?? '').trim());
}

/** Источник картинки: `http(s)://` или путь сайта; `file:`, `cid:`, `data:`, `blob:` — нет. */
export function isAllowedImageSrc(src: string | null | undefined): boolean {
  const value = (src ?? '').trim();
  return isSitePath(value) || /^https?:\/\//i.test(value);
}
