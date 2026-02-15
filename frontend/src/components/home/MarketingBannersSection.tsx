/**
 * MarketingBannersSection Component
 *
 * Карусель маркетинговых баннеров под блоком QuickLinksSection.
 * Использует bannersService.getActive('marketing') для получения данных.
 * Обернут в ErrorBoundary с fallback null — падение секции не ломает HomePage.
 *
 * @see _bmad-output/implementation-artifacts/32-4-marketing-banners-ui.md
 */

'use client';

import React, { useState, useEffect, useCallback, Component } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import bannersService from '@/services/bannersService';
import { useBannerCarousel } from '@/hooks/useBannerCarousel';
import type { Banner } from '@/types/banners';

// ---------------------------------------------------------------------------
// ErrorBoundary (component-level, fallback: null)
// ---------------------------------------------------------------------------

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class MarketingBannerErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}

// ---------------------------------------------------------------------------
// Skeleton Loader
// ---------------------------------------------------------------------------

const MarketingBannersSkeleton: React.FC = () => (
  <section
    className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 py-4 md:py-6"
    aria-label="Маркетинговые баннеры загружаются"
    data-testid="marketing-banners-skeleton"
  >
    <div className="relative w-full aspect-[21/9] md:aspect-[3/1] bg-gray-200 rounded-2xl animate-pulse" />
  </section>
);

// ---------------------------------------------------------------------------
// MarketingBannersCarousel (inner component)
// ---------------------------------------------------------------------------

const MarketingBannersCarousel: React.FC = () => {
  const [banners, setBanners] = useState<Banner[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [failedImages, setFailedImages] = useState<Set<number>>(new Set());

  const {
    emblaRef,
    selectedIndex,
    scrollSnaps,
    onDotButtonClick,
  } = useBannerCarousel({
    loop: true,
    autoplay: true,
    autoplayDelay: 5000,
  });

  useEffect(() => {
    const loadBanners = async () => {
      try {
        setIsLoading(true);
        const data = await bannersService.getActive('marketing');
        setBanners(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load marketing banners:', err);
        setError(err instanceof Error ? err : new Error('Unknown error'));
      } finally {
        setIsLoading(false);
      }
    };

    loadBanners();
  }, []);

  const handleImageError = useCallback((bannerId: number) => {
    setFailedImages(prev => {
      const next = new Set(prev);
      next.add(bannerId);
      return next;
    });
  }, []);

  // Loading state — skeleton
  if (isLoading) {
    return <MarketingBannersSkeleton />;
  }

  // Error or empty — hide section (AC2)
  if (error || banners.length === 0) {
    return null;
  }

  // Filter out banners with failed images
  const visibleBanners = banners.filter(b => !failedImages.has(b.id));

  // All images failed — hide section
  if (visibleBanners.length === 0) {
    return null;
  }

  return (
    <section
      className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6 py-4 md:py-6"
      aria-label="Маркетинговые предложения"
      data-testid="marketing-banners-section"
    >
      <div ref={emblaRef} className="overflow-hidden rounded-2xl">
        <div className="flex">
          {banners.map(banner => {
            const isFailed = failedImages.has(banner.id);
            if (isFailed) return null;

            return (
              <div
                className="flex-[0_0_100%] min-w-0 relative"
                key={banner.id}
              >
                <Link
                  href={banner.cta_link}
                  className="block relative w-full aspect-[21/9] md:aspect-[3/1]"
                  aria-label={banner.title}
                >
                  <Image
                    src={banner.image_url}
                    alt={banner.image_alt}
                    fill
                    sizes="(max-width: 768px) 100vw, 1280px"
                    className="object-cover"
                    loading="lazy"
                    onError={() => handleImageError(banner.id)}
                  />
                </Link>
              </div>
            );
          })}
        </div>
      </div>

      {/* Dots navigation — only when more than 1 visible banner */}
      {visibleBanners.length > 1 && (
        <div
          className="flex gap-2 justify-center mt-3"
          role="tablist"
          aria-label="Навигация по баннерам"
        >
          {scrollSnaps.map((_, index) => (
            <button
              key={index}
              onClick={() => onDotButtonClick(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === selectedIndex ? 'bg-cyan-600 w-8' : 'bg-gray-300'
              }`}
              role="tab"
              aria-selected={index === selectedIndex}
              aria-label={`Баннер ${index + 1}`}
            />
          ))}
        </div>
      )}
    </section>
  );
};

// ---------------------------------------------------------------------------
// Public export: wrapped in ErrorBoundary
// ---------------------------------------------------------------------------

export const MarketingBannersSection: React.FC = () => (
  <MarketingBannerErrorBoundary>
    <MarketingBannersCarousel />
  </MarketingBannerErrorBoundary>
);

MarketingBannersSection.displayName = 'MarketingBannersSection';

// Export ErrorBoundary for testing
export { MarketingBannerErrorBoundary };
