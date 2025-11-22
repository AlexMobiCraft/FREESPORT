/**
 * HeroSection Component
 *
 * Hero-секция главной страницы с динамическими баннерами
 * адаптированными под роль пользователя (B2B/B2C/Guest)
 */

'use client';

import Image from 'next/image';
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
    <section className="relative overflow-hidden text-white py-16" aria-label="Hero section">
      <div
        className="absolute inset-0 bg-gradient-to-br from-[#111827] to-[#1f2937]"
        aria-hidden="true"
      />

      <div className="relative mx-auto px-3 md:px-4 lg:px-6 max-w-[1280px] flex flex-col-reverse gap-10 md:flex-row md:items-center">
        <div className="text-center md:text-left max-w-2xl">
          {/* Hero заголовок - typography.display-l */}
          <h1 className="text-5xl font-bold mb-6 text-white">{bannerContent.title}</h1>

          {/* Подзаголовок - typography.body-l */}
          <p className="text-lg font-medium mb-8 mx-auto md:mx-0 text-[#E5E7EB] max-w-3xl">
            {bannerContent.subtitle}
          </p>

          {/* CTA кнопка - height 56px, radius 16px */}
          <div className="flex justify-center md:justify-start">
            <Link href={bannerContent.cta.link}>
              <Button
                variant="primary"
                size="large"
                className="h-14 rounded-2xl shadow-[0_0_30px_rgba(8,145,178,0.35)]"
              >
                {bannerContent.cta.text}
              </Button>
            </Link>
          </div>
        </div>

        <div className="flex w-full items-center justify-center md:justify-end">
          <div className="relative w-full max-w-[480px]">
            <Image
              src="/og-image.jpg"
              alt="FREESPORT — подборка спортивных товаров"
              width={960}
              height={900}
              className="h-auto w-full rounded-[32px] object-cover shadow-[0_35px_120px_rgba(0,0,0,0.35)]"
              priority
            />
            <div className="pointer-events-none absolute inset-0 rounded-[32px] ring-1 ring-white/10" />
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
