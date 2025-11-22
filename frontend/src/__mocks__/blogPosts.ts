/**
 * Mock данные для блога (Story 12.7)
 */

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
    title: 'Новая коллекция беговой экипировки',
    excerpt: 'Встречайте обновленную линейку кроссовок и одежды для бега на длинные дистанции.',
    image: '/images/blog/running-shoes.jpg',
    date: '2025-11-15',
    slug: 'novaya-kollekciya-begovoy-ekipirovki',
    author: 'Редакция FREESPORT',
    category: 'Коллекции',
  },
  {
    id: '2',
    title: 'Скидки на фитнес-оборудование',
    excerpt: 'Специальные цены на гантели, гири и тренажеры. Акция действует до конца месяца.',
    image: '/images/blog/fitnes.jpg',
    date: '2025-11-12',
    slug: 'skidki-na-fitnes-oborudovanie',
    author: 'Редакция FREESPORT',
    category: 'Акции',
  },
  {
    id: '3',
    title: 'Скидки на фитнес-оборудование',
    excerpt: 'Специальные цены на гантели, гири и тренажеры. Акция действует до конца месяца.',
    image: '/images/blog/mosow-shop.jpg',
    date: '2025-11-10',
    slug: 'skidki-na-fitnes-oborudovanie-2',
    author: 'Редакция FREESPORT',
    category: 'Акции',
  },
];
