/**
 * HeroSection Component
 *
 * Hero-секция главной страницы с динамическими баннерами
 * адаптированными под роль пользователя (B2B/B2C/Guest)
 */

'use client';

import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { Button } from '@/components/ui/Button/Button';

interface BannerContent {
  title: string;
  subtitle: string;
  cta: {
    text: string;
    link: string;
  };
}

const HeroSection = () => {
  const { user } = useAuthStore();

  // Определение контента баннера на основе роли пользователя
  const getBannerContent = (): BannerContent => {
    // B2B пользователи (wholesale)
    if (
      user?.role === 'wholesale_level1' ||
      user?.role === 'wholesale_level2' ||
      user?.role === 'wholesale_level3'
    ) {
      return {
        title: 'Оптовые поставки спортивных товаров',
        subtitle: 'Специальные цены для бизнеса. Персональный менеджер и гибкие условия.',
        cta: {
          text: 'Узнать оптовые условия',
          link: '/wholesale',
        },
      };
    }

    // B2C пользователи (retail)
    if (user?.role === 'retail') {
      return {
        title: 'Новая коллекция 2025',
        subtitle: 'Стиль и качество для вашего спорта. Эксклюзивные новинки уже в продаже.',
        cta: {
          text: 'Перейти в каталог',
          link: '/catalog',
        },
      };
    }

    // Неавторизованные пользователи (универсальный баннер)
    return {
      title: 'FREESPORT - Спортивные товары для профессионалов и любителей',
      subtitle: '5 брендов. 1000+ товаров. Доставка по всей России.',
      cta: {
        text: 'Начать покупки',
        link: '/catalog',
      },
    };
  };

  const bannerContent = getBannerContent();

  return (
    <section
      className="relative bg-[#F5F7FB] text-primary"
      aria-label="Hero section"
      style={{ paddingTop: '64px', paddingBottom: '64px' }}
    >
      <div className="mx-auto px-3 md:px-4 lg:px-6 max-w-[1280px]">
        <div className="text-center md:text-left">
          {/* Hero заголовок - typography.display-l */}
          <h1 className="text-5xl font-bold mb-6 text-primary">{bannerContent.title}</h1>

          {/* Подзаголовок - typography.body-l */}
          <p className="text-lg font-medium mb-8 mx-auto md:mx-0 text-secondary max-w-3xl">
            {bannerContent.subtitle}
          </p>

          {/* CTA кнопка - height 56px, radius 16px */}
          <div className="flex justify-center md:justify-start">
            <Link href={bannerContent.cta.link}>
              <Button variant="primary" size="large" className="h-14 rounded-2xl">
                {bannerContent.cta.text}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
