/**
 * useBannerCarousel Hook Tests
 * Tests for the carousel hook with Embla Carousel integration
 *
 * @see _bmad-output/implementation-artifacts/32-3-frontend-carousel-logic.md
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useBannerCarousel } from '../useBannerCarousel';
import type { UseBannerCarouselOptions } from '../useBannerCarousel';

// Mock Embla Carousel
const mockEmblaApi = {
  scrollNext: vi.fn(),
  scrollPrev: vi.fn(),
  scrollTo: vi.fn(),
  canScrollNext: vi.fn(() => true),
  canScrollPrev: vi.fn(() => false),
  selectedScrollSnap: vi.fn(() => 0),
  scrollSnapList: vi.fn(() => [0, 1, 2]),
  on: vi.fn(),
  off: vi.fn(),
  destroy: vi.fn(),
  reInit: vi.fn(),
};

vi.mock('embla-carousel-react', () => ({
  default: vi.fn(() => [vi.fn(), mockEmblaApi]),
}));

vi.mock('embla-carousel-autoplay', () => ({
  default: vi.fn(() => ({
    name: 'autoplay',
    options: {},
    init: vi.fn(),
    destroy: vi.fn(),
    play: vi.fn(),
    stop: vi.fn(),
    reset: vi.fn(),
  })),
}));

describe('useBannerCarousel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock implementations
    mockEmblaApi.selectedScrollSnap.mockReturnValue(0);
    mockEmblaApi.scrollSnapList.mockReturnValue([0, 1, 2]);
    mockEmblaApi.canScrollNext.mockReturnValue(true);
    mockEmblaApi.canScrollPrev.mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initial State', () => {
    it('should return emblaRef for container attachment', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(result.current.emblaRef).toBeDefined();
      expect(typeof result.current.emblaRef).toBe('function');
    });

    it('should return selectedIndex initialized to 0', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(result.current.selectedIndex).toBe(0);
    });

    it('should return scrollSnaps array', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(Array.isArray(result.current.scrollSnaps)).toBe(true);
    });

    it('should return canScrollPrev and canScrollNext booleans', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(typeof result.current.canScrollPrev).toBe('boolean');
      expect(typeof result.current.canScrollNext).toBe('boolean');
    });
  });

  describe('API Methods', () => {
    it('should expose scrollNext method', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(typeof result.current.scrollNext).toBe('function');
    });

    it('should expose scrollPrev method', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(typeof result.current.scrollPrev).toBe('function');
    });

    it('should expose onDotButtonClick method', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(typeof result.current.onDotButtonClick).toBe('function');
    });

    it('should call emblaApi.scrollNext when scrollNext is invoked', () => {
      const { result } = renderHook(() => useBannerCarousel());

      act(() => {
        result.current.scrollNext();
      });

      expect(mockEmblaApi.scrollNext).toHaveBeenCalled();
    });

    it('should call emblaApi.scrollPrev when scrollPrev is invoked', () => {
      const { result } = renderHook(() => useBannerCarousel());

      act(() => {
        result.current.scrollPrev();
      });

      expect(mockEmblaApi.scrollPrev).toHaveBeenCalled();
    });

    it('should call emblaApi.scrollTo when onDotButtonClick is invoked with index', () => {
      const { result } = renderHook(() => useBannerCarousel());

      act(() => {
        result.current.onDotButtonClick(2);
      });

      expect(mockEmblaApi.scrollTo).toHaveBeenCalledWith(2);
    });
  });

  describe('Options Configuration', () => {
    it('should accept loop option', () => {
      const options: UseBannerCarouselOptions = { loop: true };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });

    it('should accept align option', () => {
      const options: UseBannerCarouselOptions = { align: 'center' };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });

    it('should accept autoplay option', () => {
      const options: UseBannerCarouselOptions = { autoplay: true };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });

    it('should accept autoplayDelay option', () => {
      const options: UseBannerCarouselOptions = {
        autoplay: true,
        autoplayDelay: 5000,
      };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });

    it('should accept stopOnInteraction option', () => {
      const options: UseBannerCarouselOptions = {
        autoplay: true,
        stopOnInteraction: false,
      };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });
  });

  describe('Event Listeners', () => {
    it('should register init and select event listeners', async () => {
      renderHook(() => useBannerCarousel());

      await waitFor(() => {
        const onCalls = mockEmblaApi.on.mock.calls;
        const eventNames = onCalls.map(call => call[0]);

        expect(eventNames).toContain('select');
        expect(eventNames).toContain('init');
      });
    });

    it('should register reInit event listener', async () => {
      renderHook(() => useBannerCarousel());

      await waitFor(() => {
        const onCalls = mockEmblaApi.on.mock.calls;
        const eventNames = onCalls.map(call => call[0]);

        expect(eventNames).toContain('reInit');
      });
    });
  });

  describe('Type Safety', () => {
    it('should return correctly typed UseBannerCarouselReturn object', () => {
      const { result } = renderHook(() => useBannerCarousel());

      // Type assertions - these will fail at compile time if types are wrong
      const _emblaRef: typeof result.current.emblaRef = result.current.emblaRef;
      const _selectedIndex: number = result.current.selectedIndex;
      const _scrollSnaps: number[] = result.current.scrollSnaps;
      const _canScrollPrev: boolean = result.current.canScrollPrev;
      const _canScrollNext: boolean = result.current.canScrollNext;
      const _scrollNext: () => void = result.current.scrollNext;
      const _scrollPrev: () => void = result.current.scrollPrev;
      const _onDotButtonClick: (index: number) => void = result.current.onDotButtonClick;

      // Suppress unused variable warnings
      void _emblaRef;
      void _selectedIndex;
      void _scrollSnaps;
      void _canScrollPrev;
      void _canScrollNext;
      void _scrollNext;
      void _scrollPrev;
      void _onDotButtonClick;

      expect(true).toBe(true);
    });
  });
});
