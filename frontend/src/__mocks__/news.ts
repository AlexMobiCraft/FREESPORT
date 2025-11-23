/**
 * Статические данные для новостей (fallback для /news)
 */

export interface StaticNewsItem {
  id: number;
  title: string;
  excerpt: string;
  image: string;
  published_at: string;
}

export const STATIC_NEWS_ITEMS: StaticNewsItem[] = [
  {
    id: 1,
    title: 'Новое поступление беговой экипировки',
    excerpt: 'Рассказываем о ключевых моделях и технологиях в свежей коллекции.',
    image: '/images/new/running-shoes.jpg',
    published_at: '2025-11-15T10:00:00+03:00',
  },
  {
    id: 2,
    title: 'Фитнес-оборудование со скидками',
    excerpt: 'Гантели, гири и тренажёры доступны по специальным ценам до конца месяца.',
    image: '/images/new/fitnes.jpg',
    published_at: '2025-11-12T10:00:00+03:00',
  },
  {
    id: 3,
    title: 'Открытие обновлённого шоурума',
    excerpt: 'Приглашаем протестировать новинки и получить персональную консультацию.',
    image: '/images/new/mosow-shop.jpg',
    published_at: '2025-11-10T10:00:00+03:00',
  },
];
