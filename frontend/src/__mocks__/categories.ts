/**
 * Mock данные для категорий (Story 12.7)
 * Используются для development и тестирования
 *
 * TODO: Заменить placeholder изображения на реальные после завершения Epic по production assets
 */

import { categoryPlaceholder } from '@/utils/placeholders';

export const MOCK_CATEGORIES = [
  {
    id: 1,
    name: 'Футбол',
    href: '/catalog/football',
    image: categoryPlaceholder('Футбол'),
    alt: 'Спортивная одежда и инвентарь для футбола',
  },
  {
    id: 2,
    name: 'Фитнес',
    href: '/catalog/fitness',
    image: categoryPlaceholder('Фитнес'),
    alt: 'Товары для фитнеса и тренировок',
  },
  {
    id: 3,
    name: 'Единоборства',
    href: '/catalog/martial-arts',
    image: categoryPlaceholder('Единоборства'),
    alt: 'Экипировка для единоборств',
  },
  {
    id: 4,
    name: 'Плавание',
    href: '/catalog/swimming',
    image: categoryPlaceholder('Плавание'),
    alt: 'Товары для плавания',
  },
  {
    id: 5,
    name: 'Детский транспорт',
    href: '/catalog/kids-transport',
    image: categoryPlaceholder('Детский транспорт'),
    alt: 'Детские велосипеды, самокаты, ролики',
  },
];
