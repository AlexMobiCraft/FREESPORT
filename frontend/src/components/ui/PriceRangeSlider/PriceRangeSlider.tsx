/**
 * PriceRangeSlider Component
 * Dual-thumb range slider для выбора диапазона цен согласно Design System v2.0
 *
 * @see docs/stories/epic-12/12.5.story.md#AC6
 */

import React, { useState, useRef, useCallback } from 'react';
import { cn } from '@/utils/cn';

export interface PriceRangeSliderProps {
  /** Минимальное значение */
  min: number;
  /** Максимальное значение */
  max: number;
  /** Текущее значение [от, до] */
  value: [number, number];
  /** Callback при изменении */
  onChange: (value: [number, number]) => void;
  /** Шаг изменения */
  step?: number;
  /** Функция форматирования цены */
  formatPrice?: (price: number) => string;
  /** Дополнительные классы */
  className?: string;
}

/**
 * Форматирует цену с разделителями тысяч и символом рубля
 */
const defaultFormatPrice = (price: number): string => {
  return `${price.toLocaleString('ru-RU')} ₽`;
};

/**
 * PriceRangeSlider - dual-thumb slider для диапазона цен
 */
export const PriceRangeSlider = React.forwardRef<HTMLDivElement, PriceRangeSliderProps>(
  ({ min, max, value, onChange, step = 1, formatPrice = defaultFormatPrice, className }, ref) => {
    const [minValue, maxValue] = value;
    const [isDragging, setIsDragging] = useState<'min' | 'max' | null>(null);
    const trackRef = useRef<HTMLDivElement>(null);

    // Валидация значений
    const clampValue = useCallback(
      (val: number) => {
        return Math.min(Math.max(val, min), max);
      },
      [min, max]
    );

    // Вычисление процентов для позиционирования
    const getPercent = useCallback(
      (val: number) => {
        return ((val - min) / (max - min)) * 100;
      },
      [min, max]
    );

    // Обработка изменения через input
    const handleMinInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMin = Number(e.target.value.replace(/\D/g, ''));
      const clampedMin = clampValue(newMin);

      // Валидация: min не должен быть больше max
      if (clampedMin <= maxValue) {
        onChange([clampedMin, maxValue]);
      }
    };

    const handleMaxInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newMax = Number(e.target.value.replace(/\D/g, ''));
      const clampedMax = clampValue(newMax);

      // Валидация: max не должен быть меньше min
      if (clampedMax >= minValue) {
        onChange([minValue, clampedMax]);
      }
    };

    // Обработка перетаскивания thumb
    const handleMouseDown = (thumb: 'min' | 'max') => (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(thumb);
    };

    // Вычисление нового значения на основе позиции мыши
    const calculateValue = useCallback(
      (clientX: number) => {
        if (!trackRef.current) return null;

        const rect = trackRef.current.getBoundingClientRect();
        const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
        const rawValue = (percent / 100) * (max - min) + min;
        const steppedValue = Math.round(rawValue / step) * step;

        return clampValue(steppedValue);
      },
      [min, max, step, clampValue]
    );

    // Обработка движения мыши
    React.useEffect(() => {
      if (!isDragging) return;

      const handleMouseMove = (e: MouseEvent) => {
        const newValue = calculateValue(e.clientX);
        if (newValue === null) return;

        if (isDragging === 'min' && newValue <= maxValue) {
          onChange([newValue, maxValue]);
        } else if (isDragging === 'max' && newValue >= minValue) {
          onChange([minValue, newValue]);
        }
      };

      const handleMouseUp = () => {
        setIsDragging(null);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }, [isDragging, minValue, maxValue, onChange, calculateValue]);

    const minPercent = getPercent(minValue);
    const maxPercent = getPercent(maxValue);

    return (
      <div ref={ref} className={cn('w-full', className)}>
        {/* Input Fields */}
        <div className="flex items-center gap-3 mb-6">
          {/* Min Input */}
          <div className="flex-1">
            <label className="block text-caption text-text-muted mb-1">От</label>
            <input
              type="text"
              value={minValue.toLocaleString('ru-RU')}
              onChange={handleMinInputChange}
              className={cn(
                'w-full h-10 px-3 rounded-md',
                'text-body-m text-text-primary text-right',
                'bg-white',
                'border border-[#D0D7E6]',
                'transition-colors duration-[180ms]',
                'focus:outline-none focus:border-[#0060FF] focus:border-[1.5px]'
              )}
              aria-label="Минимальная цена"
            />
          </div>

          <span className="text-text-muted mt-6">—</span>

          {/* Max Input */}
          <div className="flex-1">
            <label className="block text-caption text-text-muted mb-1">До</label>
            <input
              type="text"
              value={maxValue.toLocaleString('ru-RU')}
              onChange={handleMaxInputChange}
              className={cn(
                'w-full h-10 px-3 rounded-md',
                'text-body-m text-text-primary text-right',
                'bg-white',
                'border border-[#D0D7E6]',
                'transition-colors duration-[180ms]',
                'focus:outline-none focus:border-[#0060FF] focus:border-[1.5px]'
              )}
              aria-label="Максимальная цена"
            />
          </div>
        </div>

        {/* Slider Track */}
        <div className="relative pt-2 pb-2">
          {/* Background Track - Design System v2.0 */}
          <div
            ref={trackRef}
            role="button"
            tabIndex={0}
            aria-label="Диапазон цен"
            className="relative h-1 bg-[#E3E8F2] rounded-full cursor-pointer"
            onClick={e => {
              const newValue = calculateValue(e.clientX);
              if (newValue === null) return;

              // Определяем к какому thumb ближе
              const distToMin = Math.abs(newValue - minValue);
              const distToMax = Math.abs(newValue - maxValue);

              if (distToMin < distToMax) {
                if (newValue <= maxValue) {
                  onChange([newValue, maxValue]);
                }
              } else {
                if (newValue >= minValue) {
                  onChange([minValue, newValue]);
                }
              }
            }}
            onKeyDown={event => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                const rect = trackRef.current?.getBoundingClientRect();
                if (!rect) return;
                const relativeX =
                  event.key === 'Enter' ? rect.left + rect.width / 2 : rect.left + rect.width / 2;
                const newValue = calculateValue(relativeX);
                if (newValue === null) return;
                const distToMin = Math.abs(newValue - minValue);
                const distToMax = Math.abs(newValue - maxValue);
                if (distToMin < distToMax && newValue <= maxValue) {
                  onChange([newValue, maxValue]);
                } else if (newValue >= minValue) {
                  onChange([minValue, newValue]);
                }
              }
            }}
          >
            {/* Active Track - Design System v2.0: #0060FF */}
            <div
              className="absolute h-full bg-[#0060FF] rounded-full"
              style={{
                left: `${minPercent}%`,
                right: `${100 - maxPercent}%`,
              }}
            />

            {/* Min Thumb - Design System v2.0 */}
            <div
              className={cn(
                'absolute top-1/2 -translate-y-1/2 -translate-x-1/2',
                'w-5 h-5', // 20px
                'bg-white rounded-full',
                'border-2 border-[#0060FF]',
                'cursor-grab active:cursor-grabbing',
                'transition-shadow duration-[120ms]',
                'hover:shadow-lg',
                isDragging === 'min' && 'shadow-lg scale-110'
              )}
              style={{ left: `${minPercent}%` }}
              onMouseDown={handleMouseDown('min')}
              role="slider"
              aria-valuemin={min}
              aria-valuemax={max}
              aria-valuenow={minValue}
              aria-label="Минимальная цена"
              tabIndex={0}
            />

            {/* Max Thumb - Design System v2.0 */}
            <div
              className={cn(
                'absolute top-1/2 -translate-y-1/2 -translate-x-1/2',
                'w-5 h-5', // 20px
                'bg-white rounded-full',
                'border-2 border-[#0060FF]',
                'cursor-grab active:cursor-grabbing',
                'transition-shadow duration-[120ms]',
                'hover:shadow-lg',
                isDragging === 'max' && 'shadow-lg scale-110'
              )}
              style={{ left: `${maxPercent}%` }}
              onMouseDown={handleMouseDown('max')}
              role="slider"
              aria-valuemin={min}
              aria-valuemax={max}
              aria-valuenow={maxValue}
              aria-label="Максимальная цена"
              tabIndex={0}
            />
          </div>

          {/* Min/Max Labels */}
          <div className="flex justify-between mt-2 text-caption text-text-muted">
            <span>{formatPrice(min)}</span>
            <span>{formatPrice(max)}</span>
          </div>
        </div>
      </div>
    );
  }
);

PriceRangeSlider.displayName = 'PriceRangeSlider';
