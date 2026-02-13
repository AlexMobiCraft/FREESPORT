/**
 * useBannerCarousel Hook
 * Carousel hook with Embla Carousel integration for marketing banners
 *
 * @see _bmad-output/implementation-artifacts/32-3-frontend-carousel-logic.md
 */

import { useState, useCallback, useEffect } from 'react';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';
import type { EmblaOptionsType, EmblaCarouselType } from 'embla-carousel';

/**
 * Опции для useBannerCarousel хука
 */
export interface UseBannerCarouselOptions {
  /** Включить бесконечную прокрутку (default: true) */
  loop?: boolean;
  /** Выравнивание слайдов: 'start' | 'center' | 'end' (default: 'start') */
  align?: EmblaOptionsType['align'];
  /** Включить автопрокрутку (default: false) */
  autoplay?: boolean;
  /** Задержка автопрокрутки в мс (default: 4000) */
  autoplayDelay?: number;
  /** Остановить автопрокрутку при взаимодействии (default: true) */
  stopOnInteraction?: boolean;
}

/**
 * Возвращаемое значение useBannerCarousel хука
 */
export interface UseBannerCarouselReturn {
  /** Ref для контейнера карусели (viewport) */
  emblaRef: ReturnType<typeof useEmblaCarousel>[0];
  /** Текущий индекс выбранного слайда */
  selectedIndex: number;
  /** Массив scroll snap позиций (для точек навигации) */
  scrollSnaps: number[];
  /** Можно ли прокрутить назад */
  canScrollPrev: boolean;
  /** Можно ли прокрутить вперед */
  canScrollNext: boolean;
  /** Прокрутить к следующему слайду */
  scrollNext: () => void;
  /** Прокрутить к предыдущему слайду */
  scrollPrev: () => void;
  /** Прокрутить к слайду по индексу (для точек навигации) */
  onDotButtonClick: (index: number) => void;
}

/**
 * Хук для создания карусели баннеров с поддержкой свайпов и автопрокрутки
 *
 * @param options - Опции карусели
 * @returns Объект с ref, состоянием и методами управления каруселью
 *
 * @example
 * ```tsx
 * const {
 *   emblaRef,
 *   selectedIndex,
 *   scrollSnaps,
 *   canScrollPrev,
 *   canScrollNext,
 *   scrollNext,
 *   scrollPrev,
 *   onDotButtonClick,
 * } = useBannerCarousel({
 *   loop: true,
 *   autoplay: true,
 *   autoplayDelay: 5000,
 * });
 *
 * return (
 *   <div ref={emblaRef} className="embla">
 *     <div className="embla__container">
 *       {slides.map((slide) => (
 *         <div className="embla__slide" key={slide.id}>{slide.content}</div>
 *       ))}
 *     </div>
 *   </div>
 * );
 * ```
 */
export function useBannerCarousel(options: UseBannerCarouselOptions = {}): UseBannerCarouselReturn {
  const {
    loop = true,
    align = 'start',
    autoplay = false,
    autoplayDelay = 4000,
    stopOnInteraction = true,
  } = options;

  // State for navigation
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [scrollSnaps, setScrollSnaps] = useState<number[]>([]);
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);

  // Embla options
  const emblaOptions: EmblaOptionsType = {
    loop,
    align,
  };

  // Autoplay plugin configuration
  const plugins = autoplay
    ? [
        Autoplay({
          delay: autoplayDelay,
          stopOnInteraction,
          stopOnMouseEnter: true,
        }),
      ]
    : [];

  // Initialize Embla Carousel
  const [emblaRef, emblaApi] = useEmblaCarousel(emblaOptions, plugins);

  /**
   * Обновление состояния навигации на основе текущего состояния Embla
   */
  const onSelect = useCallback((embla: EmblaCarouselType) => {
    setSelectedIndex(embla.selectedScrollSnap());
    setCanScrollPrev(embla.canScrollPrev());
    setCanScrollNext(embla.canScrollNext());
  }, []);

  /**
   * Инициализация scroll snaps
   */
  const onInit = useCallback((embla: EmblaCarouselType) => {
    setScrollSnaps(embla.scrollSnapList());
  }, []);

  /**
   * Прокрутка к следующему слайду
   */
  const scrollNext = useCallback(() => {
    if (emblaApi) emblaApi.scrollNext();
  }, [emblaApi]);

  /**
   * Прокрутка к предыдущему слайду
   */
  const scrollPrev = useCallback(() => {
    if (emblaApi) emblaApi.scrollPrev();
  }, [emblaApi]);

  /**
   * Прокрутка к слайду по индексу (для точек навигации)
   */
  const onDotButtonClick = useCallback(
    (index: number) => {
      if (emblaApi) emblaApi.scrollTo(index);
    },
    [emblaApi]
  );

  // Subscribe to Embla events
  useEffect(() => {
    if (!emblaApi) return;

    // Initial state setup
    onInit(emblaApi);
    onSelect(emblaApi);

    // Register event listeners
    emblaApi.on('init', onInit);
    emblaApi.on('reInit', onInit);
    emblaApi.on('select', onSelect);
    emblaApi.on('reInit', onSelect);

    // Cleanup
    return () => {
      emblaApi.off('init', onInit);
      emblaApi.off('reInit', onInit);
      emblaApi.off('select', onSelect);
      emblaApi.off('reInit', onSelect);
    };
  }, [emblaApi, onInit, onSelect]);

  return {
    emblaRef,
    selectedIndex,
    scrollSnaps,
    canScrollPrev,
    canScrollNext,
    scrollNext,
    scrollPrev,
    onDotButtonClick,
  };
}
