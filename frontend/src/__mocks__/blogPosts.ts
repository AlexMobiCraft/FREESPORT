/**
 * Mock данные для блога (Story 12.7)
 */

import { blogPlaceholder } from '@/utils/placeholders';

export interface BlogPost {
  id: string;
  title: string;
  excerpt: string;
  image: string;
  date: string;
  slug: string;
  author?: string;
  category?: string;
}

export const MOCK_BLOG_POSTS: BlogPost[] = [
  {
    id: '1',
    title: 'Как выбрать правильные кроссовки для бега',
    excerpt: 'Подробное руководство по выбору беговой обуви: типы стопы, пронация, амортизация.',
    image: blogPlaceholder(),
    date: '2025-11-15',
    slug: 'kak-vybrat-krossovki-dlya-bega',
    author: 'Алексей Петров',
    category: 'Советы',
  },
  {
    id: '2',
    title: '10 упражнений для домашних тренировок',
    excerpt: 'Эффективный комплекс упражнений без оборудования для поддержания формы дома.',
    image: blogPlaceholder(),
    date: '2025-11-12',
    slug: '10-uprazhneniy-dlya-doma',
    author: 'Мария Иванова',
    category: 'Тренировки',
  },
  {
    id: '3',
    title: 'Обзор новых моделей велосипедов 2025',
    excerpt: 'Разбираем лучшие новинки велосипедного рынка: горные, шоссейные, городские.',
    image: blogPlaceholder(),
    date: '2025-11-08',
    slug: 'obzor-velosipedov-2025',
    author: 'Дмитрий Сидоров',
    category: 'Обзоры',
  },
];
