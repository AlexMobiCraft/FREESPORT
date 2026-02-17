'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';
import { motion } from 'motion/react';
import type { Brand } from '@/types/api';

// ---------------------------------------------------------------------------
// BrandCard (internal)
// ---------------------------------------------------------------------------

interface BrandCardProps {
  brand: Brand;
}

const BrandCard: React.FC<BrandCardProps> = ({ brand }) => {
  if (!brand.image) return null;

  return (
    <Link
      href={`/catalog?brand=${brand.slug}`}
      aria-label={brand.name}
    >
      <motion.div
        whileHover={{ scale: 1.05, opacity: 1 }}
        transition={{ duration: 0.2 }}
        className="flex items-center justify-center h-20 md:h-24 px-4 opacity-80"
      >
        <Image
          src={brand.image}
          alt={brand.name}
          width={120}
          height={60}
          sizes="(max-width: 640px) 80px, (max-width: 1024px) 100px, 120px"
          className="object-contain max-h-full w-auto"
        />
      </motion.div>
    </Link>
  );
};

// ---------------------------------------------------------------------------
// BrandsBlock
// ---------------------------------------------------------------------------

export interface BrandsBlockProps {
  brands: Brand[];
}

export const BrandsBlock: React.FC<BrandsBlockProps> = ({ brands }) => {
  const visibleBrands = brands.filter((b) => b.image);

  const [emblaRef] = useEmblaCarousel(
    {
      align: 'start',
      loop: visibleBrands.length > 1,
      slidesToScroll: 1,
      dragFree: true,
      breakpoints: {
        '(min-width: 640px)': { slidesToScroll: 2 },
        '(min-width: 1024px)': { slidesToScroll: 3 },
      },
    },
    visibleBrands.length > 1 ? [Autoplay({ delay: 3000, stopOnInteraction: true })] : []
  );

  if (visibleBrands.length === 0) return null;

  return (
    <section
      aria-label="Популярные бренды"
      data-testid="brands-block"
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 py-6 md:py-8"
    >
      <div ref={emblaRef} className="overflow-hidden">
        <div className="flex">
          {visibleBrands.map((brand) => (
            <div
              key={brand.id}
              className="flex-[0_0_33.333%] sm:flex-[0_0_25%] md:flex-[0_0_20%] lg:flex-[0_0_16.666%] min-w-0"
            >
              <BrandCard brand={brand} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
