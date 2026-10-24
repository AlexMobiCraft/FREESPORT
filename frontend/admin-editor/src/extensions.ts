/**
 * Схема редактора: что он умеет хранить и как это выглядит в HTML.
 *
 * Вывод — подмножество белого списка `sanitize_rich_html`: без `style`, `data-*`
 * и `title` у картинок, ссылки только с разрешёнными протоколами.
 */

import { Node } from '@tiptap/core';
import type { Extensions } from '@tiptap/core';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import { Table, TableCell, TableHeader, TableRow } from '@tiptap/extension-table';
import StarterKit from '@tiptap/starter-kit';

import {
  IMAGE_ALIGNMENTS,
  UPLOAD_MARKER,
  isAllowedHref,
  isAllowedImageSrc,
  isSitePath,
} from './constants';
import type { ImageAlignment } from './constants';

const ALIGN_CLASS = /(?:^|\s)align-(left|center|right)(?:\s|$)/;

function parseAlignment(element: HTMLElement): ImageAlignment | null {
  const match = (element.getAttribute('class') ?? '').match(ALIGN_CLASS);
  return match ? (match[1] as ImageAlignment) : null;
}

/** Картинка: только `src`, `alt` и класс выравнивания; `title`, размеры и прочие классы отбрасываются. */
export const ContentImage = Image.extend({
  addAttributes() {
    return {
      src: { default: null },
      alt: { default: null },
      align: {
        default: null,
        parseHTML: (element: HTMLElement) => parseAlignment(element),
        renderHTML: (attributes: { align?: string | null }) =>
          attributes.align && (IMAGE_ALIGNMENTS as readonly string[]).includes(attributes.align)
            ? { class: `align-${attributes.align}` }
            : {},
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'img[src]',
        // Только http(s):// и пути сайта: превью загрузки, data:, blob:, а из Word —
        // file:/// и cid: в текст не попадают (bleach оставил бы от них пустой <img>).
        getAttrs: (element: HTMLElement) =>
          !element.hasAttribute(UPLOAD_MARKER) && isAllowedImageSrc(element.getAttribute('src'))
            ? null
            : false,
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['img', HTMLAttributes];
  },
}).configure({ inline: false, allowBase64: false });

/**
 * Узел загрузки: превью картинки, пока файл уходит на сервер.
 *
 * Из HTML не разбирается, а сериализатор `serialize.ts` пропускает его по маркеру,
 * поэтому ни в `textarea`, ни в режим HTML он не попадает.
 */
export const ImageUploadPlaceholder = Node.create({
  name: 'imageUpload',
  group: 'block',
  atom: true,
  selectable: false,
  draggable: false,

  addAttributes() {
    return {
      uploadId: { default: null, rendered: false },
      previewSrc: { default: '', rendered: false },
    };
  },

  parseHTML() {
    return [];
  },

  renderHTML({ node }) {
    return [
      'img',
      {
        src: node.attrs.previewSrc,
        alt: '',
        class: 'rich-editor__uploading',
        [UPLOAD_MARKER]: '',
      },
    ];
  },
});

/**
 * Ссылка: внешняя открывается в новой вкладке с `rel="noopener noreferrer nofollow"`,
 * путь этого сайта — без `target` и `rel` (nofollow на своих страницах вредит SEO).
 */
const ContentLink = Link.extend({
  renderHTML({ mark, HTMLAttributes }) {
    if (isSitePath(HTMLAttributes.href)) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { target, rel, ...attributes } = HTMLAttributes;
      return ['a', attributes, 0];
    }
    return this.parent?.({ mark, HTMLAttributes }) ?? ['a', HTMLAttributes, 0];
  },
}).configure({
  openOnClick: false,
  autolink: true,
  defaultProtocol: 'https',
  isAllowedUri: url => isAllowedHref(url),
});

/** Таблица без `style` и `colgroup` с `min-width`: ширины столбцов не хранятся. */
const ContentTable = Table.extend({
  renderHTML({ HTMLAttributes }) {
    return ['table', HTMLAttributes, ['tbody', 0]];
  },
}).configure({ resizable: false });

// Ячейка — только объединение; `colwidth` и выравнивание (style) не хранятся.
const cellAttributes = () => ({
  colspan: { default: 1 },
  rowspan: { default: 1 },
  colwidth: { default: null, parseHTML: () => null, renderHTML: () => ({}) },
});

const ContentTableCell = TableCell.extend({ addAttributes: cellAttributes });
const ContentTableHeader = TableHeader.extend({ addAttributes: cellAttributes });

export function buildExtensions(): Extensions {
  return [
    StarterKit.configure({
      heading: { levels: [2, 3, 4] },
      link: false,
      // Без «хвостового» пустого абзаца: он добавлялся бы транзакцией нормализации.
      trailingNode: false,
    }),
    ContentLink,
    ContentImage,
    ImageUploadPlaceholder,
    ContentTable,
    TableRow,
    ContentTableHeader,
    ContentTableCell,
  ];
}
