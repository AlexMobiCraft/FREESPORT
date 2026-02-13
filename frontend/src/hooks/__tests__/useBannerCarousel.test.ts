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

// Hoisted mocks for vi.mock factory functions
const { mockEmblaApi, mockUseEmblaCarousel, mockAutoplay } = vi.hoisted(() => {
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

  const mockUseEmblaCarousel = vi.fn(() => [vi.fn(), mockEmblaApi]);

  const mockAutoplay = vi.fn(() => ({
    name: 'autoplay',
    options: {},
    init: vi.fn(),
    destroy: vi.fn(),
    play: vi.fn(),
    stop: vi.fn(),
    reset: vi.fn(),
  }));

  return { mockEmblaApi, mockUseEmblaCarousel, mockAutoplay };
});

vi.mock('embla-carousel-react', () => ({
  default: mockUseEmblaCarousel,
}));

vi.mock('embla-carousel-autoplay', () => ({
  default: mockAutoplay,
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

    it('should expose scrollTo method', () => {
      const { result } = renderHook(() => useBannerCarousel());

      expect(typeof result.current.scrollTo).toBe('function');
    });

    it('should call emblaApi.scrollTo when scrollTo is invoked with index', () => {
      const { result } = renderHook(() => useBannerCarousel());

      act(() => {
        result.current.scrollTo(1);
      });

      expect(mockEmblaApi.scrollTo).toHaveBeenCalledWith(1);
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

    it('should accept speed option', () => {
      const options: UseBannerCarouselOptions = { speed: 5 };
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

    it('should accept autoScroll as alias for autoplay (AC3 compatibility)', () => {
      const options: UseBannerCarouselOptions = { autoScroll: true };
      const { result } = renderHook(() => useBannerCarousel(options));

      expect(result.current.emblaRef).toBeDefined();
    });
  });

  describe('Options Passed to Embla', () => {
    it('should pass loop and align options to useEmblaCarousel', () => {
      renderHook(() => useBannerCarousel({ loop: false, align: 'center' }));

      expect(mockUseEmblaCarousel).toHaveBeenCalledWith(
        expect.objectContaining({ loop: false, align: 'center' }),
        expect.any(Array)
      );
    });

    it('should pass speed option to useEmblaCarousel when provided', () => {
      renderHook(() => useBannerCarousel({ speed: 5 }));

      expect(mockUseEmblaCarousel).toHaveBeenCalledWith(
        expect.objectContaining({ speed: 5 }),
        expect.any(Array)
      );
    });

    it('should not include speed in options when not provided', () => {
      renderHook(() => useBannerCarousel({}));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should call Autoplay with correct options when autoplay is enabled', () => {
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          autoplayDelay: 3000,
          stopOnInteraction: false,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          delay: 3000,
          stopOnInteraction: false,
        })
      );
    });

    it('should not call Autoplay when autoplay is disabled', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: false }));

      expect(mockAutoplay).not.toHaveBeenCalled();
    });

    it('should enable Autoplay when autoScroll is true (alias)', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoScroll: true }));

      expect(mockAutoplay).toHaveBeenCalled();
    });

    it('should pass stopOnMouseEnter option to Autoplay', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnMouseEnter: false,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          stopOnMouseEnter: false,
        })
      );
    });

    it('should default stopOnMouseEnter to true', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          stopOnMouseEnter: true,
        })
      );
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

  describe('State Reactivity', () => {
    it('should update selectedIndex when select event fires', async () => {
      const { result } = renderHook(() => useBannerCarousel());

      // Find the select handler
      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const selectCall = mockEmblaApi.on.mock.calls.find(call => call[0] === 'select');
      expect(selectCall).toBeDefined();

      // Simulate select event with new index
      mockEmblaApi.selectedScrollSnap.mockReturnValue(2);

      act(() => {
        selectCall![1](mockEmblaApi);
      });

      expect(result.current.selectedIndex).toBe(2);
    });

    it('should update canScrollPrev/canScrollNext when select event fires', async () => {
      const { result } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const selectCall = mockEmblaApi.on.mock.calls.find(call => call[0] === 'select');

      // Simulate state change
      mockEmblaApi.canScrollPrev.mockReturnValue(true);
      mockEmblaApi.canScrollNext.mockReturnValue(false);

      act(() => {
        selectCall![1](mockEmblaApi);
      });

      expect(result.current.canScrollPrev).toBe(true);
      expect(result.current.canScrollNext).toBe(false);
    });

    it('should update scrollSnaps when init event fires', async () => {
      const { result } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const initCall = mockEmblaApi.on.mock.calls.find(call => call[0] === 'init');

      // Simulate init with different snaps
      mockEmblaApi.scrollSnapList.mockReturnValue([0, 1, 2, 3, 4]);

      act(() => {
        initCall![1](mockEmblaApi);
      });

      expect(result.current.scrollSnaps).toEqual([0, 1, 2, 3, 4]);
    });

    it('should update scrollSnaps when reInit event fires', async () => {
      const { result } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      // Find reInit handler that updates snaps (onInit is called on reInit)
      const reInitCalls = mockEmblaApi.on.mock.calls.filter(call => call[0] === 'reInit');
      expect(reInitCalls.length).toBeGreaterThan(0);

      // Simulate reInit with new snaps
      mockEmblaApi.scrollSnapList.mockReturnValue([0, 1]);

      act(() => {
        reInitCalls[0][1](mockEmblaApi);
      });

      expect(result.current.scrollSnaps).toEqual([0, 1]);
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
      const _scrollTo: (index: number) => void = result.current.scrollTo;

      // Suppress unused variable warnings
      void _emblaRef;
      void _selectedIndex;
      void _scrollSnaps;
      void _canScrollPrev;
      void _canScrollNext;
      void _scrollNext;
      void _scrollPrev;
      void _onDotButtonClick;
      void _scrollTo;

      expect(true).toBe(true);
    });
  });
});
