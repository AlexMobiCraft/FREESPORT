import type { Metadata } from 'next';
import ComingSoonClient from './ComingSoonClient';

export const metadata: Metadata = {
  title: 'FREESPORT - Скоро открытие',
  description: 'Платформа для оптовых и розничных продаж спортивных товаров. Мы скоро вернемся!',
};

export default function ComingSoonPage() {
  return <ComingSoonClient />;
}
