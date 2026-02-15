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
// Link safety guard (AC6 security)
// ---------------------------------------------------------------------------

const isSafeLink = (link: string): boolean => {
  if (!link) return false;
  const trimmed = link.trim();
  const lower = trimmed.toLowerCase();
  if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) return false;
  if (trimmed.startsWith('//')) return false; // block protocol-relative URLs (open redirect)
  if (trimmed.startsWith('/')) return true;
  return false;
};

const getSafeHref = (link: string): string => link.trim();

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
        const validBanners = data.filter(b => b.image_url && b.image_url.trim() !== '');
        setBanners(validBanners);
        setError(null);
      } catch (err) {
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
          {visibleBanners.map(banner => (
              <div
                className="flex-[0_0_100%] min-w-0 relative"
                key={banner.id}
              >
                {isSafeLink(banner.cta_link) ? (
                  <Link
                    href={getSafeHref(banner.cta_link)}
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
                ) : (
                  <div
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
                  </div>
                )}
              </div>
          ))}
        </div>
      </div>

      {/* Dots navigation — only when more than 1 visible banner */}
      {visibleBanners.length > 1 && (
        <div
          className="flex gap-2 justify-center mt-3"
          role="group"
          aria-label="Навигация по баннерам"
        >
          {visibleBanners.map((_, index) => (
            <button
              type="button"
              key={index}
              onClick={() => onDotButtonClick(index)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === selectedIndex ? 'bg-cyan-600 w-8' : 'bg-gray-300'
              }`}
              aria-current={index === selectedIndex ? 'true' : undefined}
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
