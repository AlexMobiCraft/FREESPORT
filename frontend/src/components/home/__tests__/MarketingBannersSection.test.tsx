/**
 * Unit тесты для MarketingBannersSection
 *
 * Покрывает AC1–AC6:
 * - AC1: секция рендерится на странице
 * - AC2: пустое состояние (null)
 * - AC3: skeleton loader
 * - AC4: обработка ошибки загрузки изображения
 * - AC5: ErrorBoundary перехватывает ошибку рендера
 * - AC6: навигация по cta_link
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import {
  MarketingBannersSection,
  MarketingBannerErrorBoundary,
} from '../MarketingBannersSection';
import bannersService from '@/services/bannersService';
import type { Banner } from '@/types/banners';

// Mock bannersService
vi.mock('@/services/bannersService');

// Mock Next.js Link
vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock Next.js Image — render img with onError support
vi.mock('next/image', () => ({
  default: ({
    src,
    alt,
    onError,
    fill,
    sizes,
    loading,
    ...props
  }: {
    src: string;
    alt: string;
    onError?: () => void;
    fill?: boolean;
    sizes?: string;
    loading?: string;
    [key: string]: unknown;
  }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      onError={onError}
      data-sizes={sizes}
      data-loading={loading}
      {...props}
    />
  ),
}));

// Mock useBannerCarousel
const mockOnDotButtonClick = vi.fn();
vi.mock('@/hooks/useBannerCarousel', () => ({
  useBannerCarousel: vi.fn(() => ({
    emblaRef: vi.fn(),
    selectedIndex: 0,
    scrollSnaps: [0],
    canScrollPrev: false,
    canScrollNext: false,
    scrollNext: vi.fn(),
    scrollPrev: vi.fn(),
    onDotButtonClick: mockOnDotButtonClick,
    scrollTo: vi.fn(),
  })),
}));

// Re-import for dynamic mock control
import { useBannerCarousel } from '@/hooks/useBannerCarousel';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockMarketingBanners: Banner[] = [
  {
    id: 10,
    type: 'marketing',
    title: 'Летняя распродажа',
    subtitle: 'Скидки до 50%',
    image_url: '/media/banners/summer-sale.jpg',
    image_alt: 'Летняя распродажа баннер',
    cta_text: 'Купить со скидкой',
    cta_link: '/catalog?sale=summer',
  },
  {
    id: 11,
    type: 'marketing',
    title: 'Новая коллекция кроссовок',
    subtitle: 'Бренды Nike, Adidas, Puma',
    image_url: '/media/banners/sneakers.jpg',
    image_alt: 'Коллекция кроссовок',
    cta_text: 'Смотреть коллекцию',
    cta_link: '/catalog/sneakers',
  },
];

const singleBanner: Banner[] = [mockMarketingBanners[0]];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MarketingBannersSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: multi-banner carousel mock
    vi.mocked(useBannerCarousel).mockReturnValue({
      emblaRef: vi.fn(),
      selectedIndex: 0,
      scrollSnaps: [0, 1],
      canScrollPrev: false,
      canScrollNext: true,
      scrollNext: vi.fn(),
      scrollPrev: vi.fn(),
      onDotButtonClick: mockOnDotButtonClick,
      scrollTo: vi.fn(),
    });
  });

  // -------------------------------------------------------------------------
  // AC3: Skeleton loading state
  // -------------------------------------------------------------------------
  describe('AC3: Состояние загрузки', () => {
    it('должен показывать skeleton loader во время загрузки', () => {
      vi.mocked(bannersService.getActive).mockReturnValue(new Promise(() => {}));

      render(<MarketingBannersSection />);

      expect(screen.getByTestId('marketing-banners-skeleton')).toBeInTheDocument();
      expect(
        screen.getByLabelText('Маркетинговые баннеры загружаются')
      ).toBeInTheDocument();
    });

    it('skeleton должен содержать контейнер с фиксированным aspect-ratio', () => {
      vi.mocked(bannersService.getActive).mockReturnValue(new Promise(() => {}));

      const { container } = render(<MarketingBannersSection />);

      const skeleton = container.querySelector('[class*="aspect-"]');
      expect(skeleton).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // AC2: Пустое состояние
  // -------------------------------------------------------------------------
  describe('AC2: Пустое состояние', () => {
    it('должен рендерить null при пустом ответе API', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue([]);

      const { container } = render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.queryByTestId('marketing-banners-skeleton')
        ).not.toBeInTheDocument();
      });

      expect(
        screen.queryByTestId('marketing-banners-section')
      ).not.toBeInTheDocument();
      expect(container.innerHTML).toBe('');
    });

    it('должен рендерить null при ошибке API', async () => {
      vi.mocked(bannersService.getActive).mockRejectedValue(
        new Error('Network Error')
      );

      const { container } = render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.queryByTestId('marketing-banners-skeleton')
        ).not.toBeInTheDocument();
      });

      expect(container.innerHTML).toBe('');
    });
  });

  // -------------------------------------------------------------------------
  // AC1: Рендеринг секции
  // -------------------------------------------------------------------------
  describe('AC1: Рендеринг секции', () => {
    it('должен рендерить секцию с баннерами после успешной загрузки', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.getByTestId('marketing-banners-section')
        ).toBeInTheDocument();
      });

      expect(
        screen.getByLabelText('Маркетинговые предложения')
      ).toBeInTheDocument();
    });

    it('должен вызывать bannersService.getActive с типом marketing', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(bannersService.getActive).toHaveBeenCalledWith('marketing');
      });
    });

    it('должен рендерить изображения с корректными alt и sizes', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(singleBanner);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const img = screen.getByAltText('Летняя распродажа баннер');
        expect(img).toBeInTheDocument();
        expect(img).toHaveAttribute(
          'data-sizes',
          '(max-width: 768px) 100vw, 1280px'
        );
      });
    });
  });

  // -------------------------------------------------------------------------
  // AC6: Навигация по cta_link
  // -------------------------------------------------------------------------
  describe('AC6: Навигация по cta_link', () => {
    it('должен оборачивать баннер в ссылку с cta_link', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(singleBanner);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const link = screen.getByRole('link', { name: 'Летняя распродажа' });
        expect(link).toHaveAttribute('href', '/catalog?sale=summer');
      });
    });

    it('должен рендерить ссылки для всех баннеров', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const links = screen.getAllByRole('link');
        expect(links).toHaveLength(2);
        expect(links[0]).toHaveAttribute('href', '/catalog?sale=summer');
        expect(links[1]).toHaveAttribute('href', '/catalog/sneakers');
      });
    });
  });

  // -------------------------------------------------------------------------
  // Dots / carousel controls
  // -------------------------------------------------------------------------
  describe('Навигация карусели', () => {
    it('должен показывать dots при banners.length > 1', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const dots = screen.getAllByRole('tab');
        expect(dots).toHaveLength(2);
      });
    });

    it('не должен показывать dots при одном баннере', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(singleBanner);
      vi.mocked(useBannerCarousel).mockReturnValue({
        emblaRef: vi.fn(),
        selectedIndex: 0,
        scrollSnaps: [0],
        canScrollPrev: false,
        canScrollNext: false,
        scrollNext: vi.fn(),
        scrollPrev: vi.fn(),
        onDotButtonClick: mockOnDotButtonClick,
        scrollTo: vi.fn(),
      });

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(screen.getByTestId('marketing-banners-section')).toBeInTheDocument();
      });

      expect(screen.queryByRole('tab')).not.toBeInTheDocument();
    });

    it('должен вызывать onDotButtonClick при клике по точке', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const dots = screen.getAllByRole('tab');
        fireEvent.click(dots[1]);
        expect(mockOnDotButtonClick).toHaveBeenCalledWith(1);
      });
    });
  });

  // -------------------------------------------------------------------------
  // AC4: Обработка ошибки загрузки изображения
  // -------------------------------------------------------------------------
  describe('AC4: Обработка ошибки загрузки изображения', () => {
    it('должен скрывать слайд при ошибке загрузки изображения', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.getByAltText('Летняя распродажа баннер')
        ).toBeInTheDocument();
      });

      // Trigger image error on first banner
      const img = screen.getByAltText('Летняя распродажа баннер');
      fireEvent.error(img);

      await waitFor(() => {
        expect(
          screen.queryByAltText('Летняя распродажа баннер')
        ).not.toBeInTheDocument();
      });

      // Second banner should still be visible
      expect(screen.getByAltText('Коллекция кроссовок')).toBeInTheDocument();
    });

    it('должен скрывать всю секцию если все изображения не загрузились', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(singleBanner);
      vi.mocked(useBannerCarousel).mockReturnValue({
        emblaRef: vi.fn(),
        selectedIndex: 0,
        scrollSnaps: [0],
        canScrollPrev: false,
        canScrollNext: false,
        scrollNext: vi.fn(),
        scrollPrev: vi.fn(),
        onDotButtonClick: mockOnDotButtonClick,
        scrollTo: vi.fn(),
      });

      const { container } = render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.getByAltText('Летняя распродажа баннер')
        ).toBeInTheDocument();
      });

      const img = screen.getByAltText('Летняя распродажа баннер');
      fireEvent.error(img);

      await waitFor(() => {
        expect(container.innerHTML).toBe('');
      });
    });
  });

  // -------------------------------------------------------------------------
  // AC5: ErrorBoundary
  // -------------------------------------------------------------------------
  describe('AC5: ErrorBoundary', () => {
    it('должен перехватывать ошибку рендера и скрывать секцию', () => {
      const ThrowingComponent = () => {
        throw new Error('Render crash');
      };

      // Suppress console.error for expected error boundary trigger
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { container } = render(
        <MarketingBannerErrorBoundary>
          <ThrowingComponent />
        </MarketingBannerErrorBoundary>
      );

      expect(container.innerHTML).toBe('');
      consoleSpy.mockRestore();
    });

    it('должен рендерить children при отсутствии ошибок', () => {
      render(
        <MarketingBannerErrorBoundary>
          <div data-testid="child-content">Content</div>
        </MarketingBannerErrorBoundary>
      );

      expect(screen.getByTestId('child-content')).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Accessibility
  // -------------------------------------------------------------------------
  describe('Accessibility', () => {
    it('должен иметь aria-label на секции', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.getByLabelText('Маркетинговые предложения')
        ).toBeInTheDocument();
      });
    });

    it('должен иметь alt текст для каждого изображения', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        expect(
          screen.getByAltText('Летняя распродажа баннер')
        ).toBeInTheDocument();
        expect(
          screen.getByAltText('Коллекция кроссовок')
        ).toBeInTheDocument();
      });
    });

    it('dots должны иметь aria-label и role=tab', async () => {
      vi.mocked(bannersService.getActive).mockResolvedValue(mockMarketingBanners);

      render(<MarketingBannersSection />);

      await waitFor(() => {
        const dots = screen.getAllByRole('tab');
        expect(dots[0]).toHaveAttribute('aria-label', 'Баннер 1');
        expect(dots[1]).toHaveAttribute('aria-label', 'Баннер 2');
        expect(dots[0]).toHaveAttribute('aria-selected', 'true');
        expect(dots[1]).toHaveAttribute('aria-selected', 'false');
      });
    });
  });

  // -------------------------------------------------------------------------
  // displayName
  // -------------------------------------------------------------------------
  it('должен иметь displayName', () => {
    expect(MarketingBannersSection.displayName).toBe('MarketingBannersSection');
  });
});
