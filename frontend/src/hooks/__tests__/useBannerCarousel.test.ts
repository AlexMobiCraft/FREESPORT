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
    it('should pass loop, align, and dragFree options to useEmblaCarousel', () => {
      renderHook(() => useBannerCarousel({ loop: false, align: 'center' }));

      expect(mockUseEmblaCarousel).toHaveBeenCalledWith(
        expect.objectContaining({ loop: false, align: 'center', dragFree: false }),
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
    it('should register select and reInit event listeners (init handled via direct call)', async () => {
      renderHook(() => useBannerCarousel());

      await waitFor(() => {
        const onCalls = mockEmblaApi.on.mock.calls;
        const eventNames = onCalls.map(call => call[0]);

        expect(eventNames).toContain('select');
        expect(eventNames).toContain('reInit');
        // Note: 'init' subscription removed to avoid duplication with direct calls
      });
    });

    it('should register multiple reInit handlers for onInit and onSelect', async () => {
      renderHook(() => useBannerCarousel());

      await waitFor(() => {
        const reInitCalls = mockEmblaApi.on.mock.calls.filter(call => call[0] === 'reInit');
        // Should have 2 reInit handlers: onInit and onSelect
        expect(reInitCalls.length).toBe(2);
      });
    });

    it('should sync nav-state via direct calls on mount (no init subscription needed)', async () => {
      // Setup: mock returns specific values
      mockEmblaApi.selectedScrollSnap.mockReturnValue(2);
      mockEmblaApi.canScrollPrev.mockReturnValue(true);
      mockEmblaApi.canScrollNext.mockReturnValue(false);
      mockEmblaApi.scrollSnapList.mockReturnValue([0, 1, 2, 3, 4]);

      const { result } = renderHook(() => useBannerCarousel());

      // Nav state should be synced from direct onInit/onSelect calls
      await waitFor(() => {
        expect(result.current.selectedIndex).toBe(2);
        expect(result.current.canScrollPrev).toBe(true);
        expect(result.current.canScrollNext).toBe(false);
        expect(result.current.scrollSnaps).toEqual([0, 1, 2, 3, 4]);
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

  describe('Options Stability (Memoization)', () => {
    it('should maintain referential stability of emblaOptions between renders with same values', () => {
      const options: UseBannerCarouselOptions = {
        loop: true,
        align: 'center',
        autoplay: true,
        autoplayDelay: 5000,
      };

      const { rerender } = renderHook(({ opts }) => useBannerCarousel(opts), {
        initialProps: { opts: options },
      });

      const initialCallCount = mockUseEmblaCarousel.mock.calls.length;

      // Rerender with same option values (but new object reference)
      rerender({ opts: { ...options } });

      // useEmblaCarousel should be called again, but with memoized options
      const calls = mockUseEmblaCarousel.mock.calls;
      const firstOptions = calls[initialCallCount - 1][0];
      const secondOptions = calls[calls.length - 1][0];

      // Options should be REFERENTIALLY equal due to useMemo (toBe checks identity)
      expect(firstOptions).toBe(secondOptions);
    });

    it('should maintain referential stability of plugins array between renders with same autoplay config', () => {
      const { rerender } = renderHook(({ autoplay }) => useBannerCarousel({ autoplay }), {
        initialProps: { autoplay: true },
      });

      const callsBefore = mockUseEmblaCarousel.mock.calls.length;

      // Rerender with same autoplay value
      rerender({ autoplay: true });

      const callsAfter = mockUseEmblaCarousel.mock.calls.length;

      // Plugins array should be REFERENTIALLY stable (toBe checks identity)
      const pluginsBefore = mockUseEmblaCarousel.mock.calls[callsBefore - 1][1];
      const pluginsAfter = mockUseEmblaCarousel.mock.calls[callsAfter - 1][1];

      expect(pluginsBefore).toBe(pluginsAfter);
    });

    it('should reinitialize when autoplay changes from false to true', () => {
      mockAutoplay.mockClear();

      const { rerender } = renderHook(({ autoplay }) => useBannerCarousel({ autoplay }), {
        initialProps: { autoplay: false },
      });

      expect(mockAutoplay).not.toHaveBeenCalled();

      rerender({ autoplay: true });

      expect(mockAutoplay).toHaveBeenCalled();
    });

    it('should maintain referential stability of empty plugins array when autoplay=false', () => {
      const { rerender } = renderHook(({ delay }) => useBannerCarousel({ autoplay: false, autoplayDelay: delay }), {
        initialProps: { delay: 4000 },
      });

      const callsBefore = mockUseEmblaCarousel.mock.calls.length;

      // Rerender with different delay (should not affect empty plugins)
      rerender({ delay: 5000 });

      const callsAfter = mockUseEmblaCarousel.mock.calls.length;

      // Empty plugins array should be REFERENTIALLY stable (same constant)
      const pluginsBefore = mockUseEmblaCarousel.mock.calls[callsBefore - 1][1];
      const pluginsAfter = mockUseEmblaCarousel.mock.calls[callsAfter - 1][1];

      expect(pluginsBefore).toBe(pluginsAfter);
      expect(pluginsBefore).toHaveLength(0);
    });
  });

  describe('Touch/Interaction Behavior (AC2/AC3)', () => {
    it('should explicitly set dragFree: false for 1:1 finger tracking (AC2)', () => {
      renderHook(() => useBannerCarousel({}));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      const emblaOptions = lastCall[0];

      // dragFree should be explicitly false (not relying on Embla default)
      expect(emblaOptions.dragFree).toBe(false);
    });

    it('should configure Autoplay to pause on mouse enter (hover pause for AC3)', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnMouseEnter: true,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          stopOnMouseEnter: true,
        })
      );
    });

    it('should configure Autoplay to pause on interaction (touch pause for AC3)', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnInteraction: true,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          stopOnInteraction: true,
        })
      );
    });

    it('should allow disabling hover pause behavior', () => {
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

    it('should allow disabling interaction pause behavior', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnInteraction: false,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({
          stopOnInteraction: false,
        })
      );
    });
  });

  describe('Behavioral Contract Tests (Mock-based)', () => {
    /**
     * These tests verify the behavioral contract of the hook using mocked Embla/Autoplay.
     * They validate API coordination, state synchronization, and configuration passing.
     *
     * NOTE: These are NOT browser-level integration tests. True integration tests
     * (swipe gestures, touch events, visual scroll) require E2E tools like Playwright
     * or Cypress with a real browser engine.
     *
     * JSDOM limitations: no layout engine, getBoundingClientRect returns zeros,
     * no IntersectionObserver, no real touch/pointer events.
     *
     * TODO: Add E2E tests in future story for complete touch/swipe verification.
     */

    it('should coordinate multiple API calls correctly', () => {
      const { result } = renderHook(() => useBannerCarousel({ loop: true }));

      // Multiple sequential API calls should work without errors
      act(() => {
        result.current.scrollNext();
        result.current.scrollPrev();
        result.current.scrollTo(1);
        result.current.onDotButtonClick(2);
      });

      // All methods should have been invoked on the API
      expect(mockEmblaApi.scrollNext).toHaveBeenCalledTimes(1);
      expect(mockEmblaApi.scrollPrev).toHaveBeenCalledTimes(1);
      expect(mockEmblaApi.scrollTo).toHaveBeenCalledTimes(2); // scrollTo + onDotButtonClick
    });

    it('should handle rapid state changes without losing sync', async () => {
      const { result } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const selectHandler = mockEmblaApi.on.mock.calls.find(c => c[0] === 'select')![1];

      // Simulate rapid state changes
      act(() => {
        mockEmblaApi.selectedScrollSnap.mockReturnValue(1);
        selectHandler(mockEmblaApi);
        mockEmblaApi.selectedScrollSnap.mockReturnValue(2);
        selectHandler(mockEmblaApi);
        mockEmblaApi.selectedScrollSnap.mockReturnValue(0);
        selectHandler(mockEmblaApi);
      });

      // Final state should match last update
      expect(result.current.selectedIndex).toBe(0);
    });

    it('should pass complete autoplay configuration to plugin', () => {
      mockAutoplay.mockClear();

      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          autoplayDelay: 3000,
          stopOnInteraction: false,
          stopOnMouseEnter: true,
        })
      );

      // Verify all autoplay options are passed together
      expect(mockAutoplay).toHaveBeenCalledWith({
        delay: 3000,
        stopOnInteraction: false,
        stopOnMouseEnter: true,
      });
    });

    it('should pass complete Embla options to useEmblaCarousel', () => {
      renderHook(() =>
        useBannerCarousel({
          loop: false,
          align: 'center',
          speed: 15,
        })
      );

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];

      expect(lastCall[0]).toEqual({
        loop: false,
        align: 'center',
        dragFree: false,
        speed: 15,
      });
    });

    it('should cleanup event listeners on unmount', async () => {
      const { unmount } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      // 3 listeners: reInit (onInit), select (onSelect), reInit (onSelect)
      const onCallCount = mockEmblaApi.on.mock.calls.length;
      expect(onCallCount).toBe(3);

      unmount();

      // All registered listeners should be unregistered
      expect(mockEmblaApi.off.mock.calls.length).toBe(onCallCount);
    });

    it('should cleanup with correct event names and handler references', async () => {
      const { unmount } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      // Capture registered handlers
      const onCalls = mockEmblaApi.on.mock.calls;
      const registeredHandlers = onCalls.map(call => ({ event: call[0], handler: call[1] }));

      unmount();

      // Verify each handler is unregistered with same event name and handler reference
      const offCalls = mockEmblaApi.off.mock.calls;
      registeredHandlers.forEach(({ event, handler }) => {
        const matchingOff = offCalls.find(
          call => call[0] === event && call[1] === handler
        );
        expect(matchingOff).toBeDefined();
      });
    });

    it('should unregister reInit handler for onInit on unmount', async () => {
      const { unmount } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const reInitOnCalls = mockEmblaApi.on.mock.calls.filter(c => c[0] === 'reInit');
      expect(reInitOnCalls.length).toBeGreaterThan(0);

      unmount();

      const reInitOffCalls = mockEmblaApi.off.mock.calls.filter(c => c[0] === 'reInit');
      expect(reInitOffCalls.length).toBe(reInitOnCalls.length);
    });

    it('should unregister select handler on unmount', async () => {
      const { unmount } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      const selectOnCall = mockEmblaApi.on.mock.calls.find(c => c[0] === 'select');
      expect(selectOnCall).toBeDefined();

      unmount();

      const selectOffCall = mockEmblaApi.off.mock.calls.find(c => c[0] === 'select');
      expect(selectOffCall).toBeDefined();
      // Handler reference should match
      expect(selectOffCall![1]).toBe(selectOnCall![1]);
    });
  });

  describe('AC3 Behavioral Contract: Auto Cycle and Pause', () => {
    /**
     * AC3: Given autoScroll: true or defined interval, carousel cycles automatically
     * and pauses on user interaction (hover or touch) if configured.
     *
     * These tests verify the behavioral contract through plugin configuration.
     * Actual pause/resume behavior depends on Embla Autoplay plugin implementation.
     */

    it('should configure auto-cycle with default 4000ms delay when autoplay=true', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 4000 })
      );
    });

    it('should configure auto-cycle with custom delay', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: 6000 }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 6000 })
      );
    });

    it('should enable pause on hover by default (stopOnMouseEnter=true)', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ stopOnMouseEnter: true })
      );
    });

    it('should enable pause on touch/interaction by default (stopOnInteraction=true)', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ stopOnInteraction: true })
      );
    });

    it('should allow continuous auto-cycle without pause on hover', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnMouseEnter: false,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ stopOnMouseEnter: false })
      );
    });

    it('should allow continuous auto-cycle without pause on interaction', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          stopOnInteraction: false,
        })
      );

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ stopOnInteraction: false })
      );
    });

    it('should pass complete pause configuration to Autoplay plugin', () => {
      mockAutoplay.mockClear();
      renderHook(() =>
        useBannerCarousel({
          autoplay: true,
          autoplayDelay: 3000,
          stopOnInteraction: true,
          stopOnMouseEnter: true,
        })
      );

      // Verify Autoplay receives all AC3 relevant options
      expect(mockAutoplay).toHaveBeenCalledWith({
        delay: 3000,
        stopOnInteraction: true,
        stopOnMouseEnter: true,
      });
    });

    it('should maintain stable autoplay plugin instance on re-render with same options', () => {
      mockAutoplay.mockClear();

      const { rerender } = renderHook(
        ({ autoplay, delay }) => useBannerCarousel({ autoplay, autoplayDelay: delay }),
        { initialProps: { autoplay: true, delay: 5000 } }
      );

      const initialAutoplayCallCount = mockAutoplay.mock.calls.length;

      // Re-render with same values
      rerender({ autoplay: true, delay: 5000 });

      // Autoplay should NOT be called again (stable instance via useRef)
      expect(mockAutoplay.mock.calls.length).toBe(initialAutoplayCallCount);
    });

    it('should recreate autoplay plugin only when options change', () => {
      mockAutoplay.mockClear();

      const { rerender } = renderHook(
        ({ delay }) => useBannerCarousel({ autoplay: true, autoplayDelay: delay }),
        { initialProps: { delay: 4000 } }
      );

      const initialCallCount = mockAutoplay.mock.calls.length;

      // Change delay - should recreate plugin
      rerender({ delay: 6000 });

      expect(mockAutoplay.mock.calls.length).toBe(initialCallCount + 1);
      expect(mockAutoplay).toHaveBeenLastCalledWith(
        expect.objectContaining({ delay: 6000 })
      );
    });
  });

  describe('Autoplay Activation Logic (AC3)', () => {
    it('should enable autoplay when autoplayDelay is provided without explicit autoplay=true', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplayDelay: 5000 }));

      // AC3: "defined interval" should activate autoplay
      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 5000 })
      );
    });

    it('should NOT enable autoplay when neither autoplay nor autoplayDelay is provided', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({}));

      expect(mockAutoplay).not.toHaveBeenCalled();
    });

    it('should respect explicit autoplay=false even with autoplayDelay provided', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: false, autoplayDelay: 5000 }));

      // Explicit false should take precedence
      expect(mockAutoplay).not.toHaveBeenCalled();
    });

    it('should respect explicit autoScroll=false even with autoplayDelay provided', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoScroll: false, autoplayDelay: 5000 }));

      // Explicit false should take precedence
      expect(mockAutoplay).not.toHaveBeenCalled();
    });

    it('should prioritize autoScroll over autoplay when both provided', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoScroll: true, autoplay: false }));

      // autoScroll takes precedence
      expect(mockAutoplay).toHaveBeenCalled();
    });

    it('should prioritize autoScroll=false over autoplay=true when both provided', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoScroll: false, autoplay: true }));

      // autoScroll takes precedence
      expect(mockAutoplay).not.toHaveBeenCalled();
    });
  });

  describe('Runtime Validation', () => {
    it('should ignore invalid speed (NaN) and use default', () => {
      renderHook(() => useBannerCarousel({ speed: NaN }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      // NaN should be filtered out
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should ignore invalid speed (<=0) and use default', () => {
      renderHook(() => useBannerCarousel({ speed: 0 }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should ignore negative speed and use default', () => {
      renderHook(() => useBannerCarousel({ speed: -5 }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should ignore invalid autoplayDelay (NaN) and use default', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: NaN }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 4000 }) // default
      );
    });

    it('should ignore invalid autoplayDelay (<=0) and use default', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: 0 }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 4000 }) // default
      );
    });

    it('should ignore negative autoplayDelay and use default', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: -1000 }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 4000 }) // default
      );
    });

    it('should accept valid positive speed', () => {
      renderHook(() => useBannerCarousel({ speed: 15 }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).toHaveProperty('speed', 15);
    });

    it('should accept valid positive autoplayDelay', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: 3000 }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 3000 })
      );
    });

    it('should ignore Infinity speed and exclude from options', () => {
      renderHook(() => useBannerCarousel({ speed: Infinity }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should ignore -Infinity speed and exclude from options', () => {
      renderHook(() => useBannerCarousel({ speed: -Infinity }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[0]).not.toHaveProperty('speed');
    });

    it('should ignore Infinity autoplayDelay and use default', () => {
      mockAutoplay.mockClear();
      renderHook(() => useBannerCarousel({ autoplay: true, autoplayDelay: Infinity }));

      expect(mockAutoplay).toHaveBeenCalledWith(
        expect.objectContaining({ delay: 4000 })
      );
    });
  });

  describe('Cleanup: Explicit off() Verification', () => {
    it('should call emblaApi.off for reInit/onInit, select/onSelect, reInit/onSelect on unmount', async () => {
      const { unmount } = renderHook(() => useBannerCarousel());

      await waitFor(() => {
        expect(mockEmblaApi.on).toHaveBeenCalled();
      });

      unmount();

      // Verify exact off() calls matching the 3 subscriptions
      const offCalls = mockEmblaApi.off.mock.calls.map(c => c[0]);
      expect(offCalls.filter(e => e === 'reInit').length).toBe(2);
      expect(offCalls.filter(e => e === 'select').length).toBe(1);
      expect(offCalls.length).toBe(3);
    });
  });

  describe('AC3 Behavioral: Autoplay Plugin Flow', () => {
    it('should pass the autoplay plugin instance to useEmblaCarousel in plugins array', () => {
      mockAutoplay.mockClear();
      const mockPlugin = { name: 'autoplay', init: vi.fn(), destroy: vi.fn() };
      mockAutoplay.mockReturnValueOnce(mockPlugin);

      renderHook(() => useBannerCarousel({ autoplay: true }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1]).toContain(mockPlugin);
    });

    it('should pass empty plugins array when autoplay is disabled', () => {
      mockAutoplay.mockClear();

      renderHook(() => useBannerCarousel({ autoplay: false }));

      const lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1]).toEqual([]);
    });

    it('should transition plugins from active to empty when autoplay is disabled', () => {
      mockAutoplay.mockClear();

      const { rerender } = renderHook(
        ({ autoplay }) => useBannerCarousel({ autoplay }),
        { initialProps: { autoplay: true } }
      );

      // Verify plugin is active
      let lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1].length).toBe(1);

      // Disable autoplay
      rerender({ autoplay: false });

      lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1]).toEqual([]);
    });

    it('should transition plugins from empty to active when autoplay is enabled', () => {
      mockAutoplay.mockClear();

      const { rerender } = renderHook(
        ({ autoplay }) => useBannerCarousel({ autoplay }),
        { initialProps: { autoplay: false } }
      );

      // Verify plugins empty
      let lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1]).toEqual([]);

      // Enable autoplay
      rerender({ autoplay: true });

      lastCall = mockUseEmblaCarousel.mock.calls[mockUseEmblaCarousel.mock.calls.length - 1];
      expect(lastCall[1].length).toBe(1);
    });
  });

  describe('Type Safety', () => {
    it('should return correctly typed UseBannerCarouselReturn object with all required properties', () => {
      const { result } = renderHook(() => useBannerCarousel());

      // Verify all properties exist and have correct runtime types
      expect(result.current.emblaRef).toBeDefined();
      expect(typeof result.current.emblaRef).toBe('function');

      expect(typeof result.current.selectedIndex).toBe('number');
      expect(result.current.selectedIndex).toBeGreaterThanOrEqual(0);

      expect(Array.isArray(result.current.scrollSnaps)).toBe(true);

      expect(typeof result.current.canScrollPrev).toBe('boolean');
      expect(typeof result.current.canScrollNext).toBe('boolean');

      expect(typeof result.current.scrollNext).toBe('function');
      expect(typeof result.current.scrollPrev).toBe('function');
      expect(typeof result.current.onDotButtonClick).toBe('function');
      expect(typeof result.current.scrollTo).toBe('function');
    });

    it('should have all 9 properties in the return object', () => {
      const { result } = renderHook(() => useBannerCarousel());

      const keys = Object.keys(result.current);
      expect(keys).toContain('emblaRef');
      expect(keys).toContain('selectedIndex');
      expect(keys).toContain('scrollSnaps');
      expect(keys).toContain('canScrollPrev');
      expect(keys).toContain('canScrollNext');
      expect(keys).toContain('scrollNext');
      expect(keys).toContain('scrollPrev');
      expect(keys).toContain('onDotButtonClick');
      expect(keys).toContain('scrollTo');
      expect(keys).toHaveLength(9);
    });
  });
});
