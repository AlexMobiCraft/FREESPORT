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
      className="relative bg-gradient-to-r from-neutral-900 to-neutral-700 text-text-inverse"
      style={{ paddingTop: '64px', paddingBottom: '64px' }}
    >
      <div className="mx-auto px-6 md:px-4 lg:px-6" style={{ maxWidth: '1280px' }}>
        <div className="text-center">
          {/* Hero заголовок - typography.display-l */}
          <h1
            className="font-bold mb-6 text-text-inverse"
            style={{
              fontSize: '48px',
              lineHeight: '56px',
              fontWeight: 700,
            }}
          >
            {bannerContent.title}
          </h1>

          {/* Подзаголовок - typography.body-l */}
          <p
            className="mb-8 mx-auto text-neutral-300"
            style={{
              fontSize: '18px',
              lineHeight: '28px',
              fontWeight: 500,
              maxWidth: '48rem',
            }}
          >
            {bannerContent.subtitle}
          </p>

          {/* CTA кнопка */}
          <div className="flex justify-center">
            <Link href={bannerContent.cta.link}>
              <Button
                variant="primary"
                size="large"
                className="bg-primary-default hover:bg-primary-hover text-text-inverse"
                style={{
                  height: '48px',
                  paddingLeft: '32px',
                  paddingRight: '32px',
                  borderRadius: '6px',
                  fontSize: '18px',
                  lineHeight: '28px',
                  fontWeight: 500,
                }}
              >
                {bannerContent.cta.text}
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Адаптивные стили для mobile/tablet */}
      <style jsx>{`
        @media (max-width: 640px) {
          h1 {
            font-size: 32px !important;
            line-height: 40px !important;
          }
          p {
            font-size: 16px !important;
            line-height: 24px !important;
          }
        }
        @media (min-width: 641px) and (max-width: 1024px) {
          h1 {
            font-size: 40px !important;
            line-height: 48px !important;
          }
        }
      `}</style>
    </section>
  );
};

export default HeroSection;
