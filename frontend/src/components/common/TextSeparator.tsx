/**
 * TextSeparator — невидимый текстовый разделитель между соседними узлами карточки.
 *
 * Зачем: `element.textContent` склеивает соседние элементы без пробела, поэтому
 * бейдж, бренд и название товара извлекаются как одно слово («НовинкаBoyBoКапа»).
 * Это ломает чтение скринридером и копирование текста со страницы (Story 41.8, FR-41-19).
 *
 * Почему `sr-only`, а не пробел в потоке: контейнеры описания карточки —
 * flex-колонки (`p-3 flex flex-col` в compact-layout `ProductCard`,
 * `p-4 flex flex-col` в grid-layout). Обычный `<span> </span>` стал бы
 * flex-элементом и добавил строку высотой line-height — вёрстка поехала бы.
 * `sr-only` даёт `position: absolute` — элемент вне потока, внешний вид
 * не меняется вообще. НЕ «упрощать» до голого пробела или текстового узла.
 *
 * @example
 * ```tsx
 * <p>{brand.name}</p>
 * <TextSeparator />
 * <h3>{product.name}</h3>
 * ```
 */

import React from 'react';

export const TextSeparator: React.FC = () => <span className="sr-only"> </span>;

TextSeparator.displayName = 'TextSeparator';
