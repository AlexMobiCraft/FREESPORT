/**
 * Electric Orange Sidebar Widget Component
 *
 * Sidebar panel with filters for catalog page
 * Features:
 * - Skewed headers (-12deg)
 * - Skewed checkboxes
 * - Price range slider with skew
 * - Dark theme styling
 *
 * @see docs/4-ux-design/00-design-system-migration/02-component-specs.md#sidebar
 */

'use client';

import React, { useState } from 'react';
import { cn } from '@/utils/cn';

// ============================================
// Types
// ============================================

export interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

export interface FilterGroup {
  id: string;
  title: string;
  options: FilterOption[];
  type: 'checkbox' | 'price';
}

export interface PriceRange {
  min: number;
  max: number;
}

export interface ElectricSidebarProps {
  /** Filter groups to display */
  filterGroups: FilterGroup[];
  /** Selected filter IDs */
  selectedFilters?: Record<string, string[]>;
  /** Price range */
  priceRange?: PriceRange;
  /** Current price values */
  currentPrice?: PriceRange;
  /** Callback when filters change */
  onFilterChange?: (groupId: string, optionId: string, checked: boolean) => void;
  /** Callback when price changes */
  onPriceChange?: (range: PriceRange) => void;
  /** Callback when apply button clicked */
  onApply?: () => void;
  /** Additional class names */
  className?: string;
}

// ============================================
// Sidebar Component
// ============================================

export function ElectricSidebar({
  filterGroups,
  selectedFilters = {},
  priceRange = { min: 1000, max: 50000 },
  currentPrice,
  onFilterChange,
  onPriceChange,
  onApply,
  className,
}: ElectricSidebarProps) {
  const [localPrice, setLocalPrice] = useState<PriceRange>(
    currentPrice || { min: priceRange.min, max: priceRange.max }
  );

  const handlePriceMinChange = (value: number) => {
    const newRange = { ...localPrice, min: Math.min(value, localPrice.max) };
    setLocalPrice(newRange);
    onPriceChange?.(newRange);
  };

  const handlePriceMaxChange = (value: number) => {
    const newRange = { ...localPrice, max: Math.max(value, localPrice.min) };
    setLocalPrice(newRange);
    onPriceChange?.(newRange);
  };

  const handleSliderChange = (value: number) => {
    setLocalPrice({ min: priceRange.min, max: value });
    onPriceChange?.({ min: priceRange.min, max: value });
  };

  return (
    <aside
      className={cn(
        'bg-[#1A1A1A] p-8 border border-[#333333]',
        'w-full max-w-[300px] h-fit',
        className
      )}
    >
      {filterGroups.map(group => (
        <div key={group.id} className="mb-8 last:mb-0">
          {/* Filter Title - Skewed */}
          <h3
            className="text-xl mb-5 pb-3 border-b border-[#333333] w-full block uppercase tracking-wide"
            style={{
              fontFamily: "'Roboto Condensed', sans-serif",
              fontWeight: 900,
              transform: 'skewX(-12deg)',
              transformOrigin: 'left',
            }}
          >
            <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>
              {group.title}
            </span>
          </h3>

          {group.type === 'checkbox' && (
            <div className="space-y-3">
              {group.options.map(option => (
                <CheckboxRow
                  key={option.id}
                  option={option}
                  checked={selectedFilters[group.id]?.includes(option.id) || false}
                  onChange={checked => onFilterChange?.(group.id, option.id, checked)}
                />
              ))}
            </div>
          )}

          {group.type === 'price' && (
            <div>
              {/* Price Inputs */}
              <div className="flex gap-3 mb-4">
                <input
                  type="number"
                  value={localPrice.min}
                  onChange={e => handlePriceMinChange(Number(e.target.value))}
                  className="w-1/2 bg-transparent border border-[#333333] px-3 py-2 text-white text-sm focus:border-[#FF6B00] focus:outline-none"
                  min={priceRange.min}
                  max={priceRange.max}
                />
                <input
                  type="number"
                  value={localPrice.max}
                  onChange={e => handlePriceMaxChange(Number(e.target.value))}
                  className="w-1/2 bg-transparent border border-[#333333] px-3 py-2 text-white text-sm focus:border-[#FF6B00] focus:outline-none"
                  min={priceRange.min}
                  max={priceRange.max}
                />
              </div>

              {/* Skewed Range Slider */}
              <div className="my-5" style={{ transform: 'skewX(-12deg)' }}>
                <input
                  type="range"
                  min={priceRange.min}
                  max={priceRange.max}
                  value={localPrice.max}
                  onChange={e => handleSliderChange(Number(e.target.value))}
                  className="w-full h-[6px] bg-[#333333] appearance-none cursor-pointer
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-[18px]
                    [&::-webkit-slider-thumb]:h-[18px]
                    [&::-webkit-slider-thumb]:bg-[#FF6B00]
                    [&::-webkit-slider-thumb]:border-2
                    [&::-webkit-slider-thumb]:border-black
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-webkit-slider-thumb]:hover:bg-white
                    [&::-webkit-slider-thumb]:transition-colors
                    [&::-moz-range-thumb]:w-[18px]
                    [&::-moz-range-thumb]:h-[18px]
                    [&::-moz-range-thumb]:bg-[#FF6B00]
                    [&::-moz-range-thumb]:border-2
                    [&::-moz-range-thumb]:border-black
                    [&::-moz-range-thumb]:cursor-pointer"
                />
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Apply Button */}
      {onApply && (
        <button
          onClick={onApply}
          className="w-full h-12 bg-[#FF6B00] text-black font-bold uppercase tracking-wide transition-all hover:bg-white hover:text-[#FF6B00]"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>Применить</span>
        </button>
      )}
    </aside>
  );
}

// ============================================
// Checkbox Row Component
// ============================================

interface CheckboxRowProps {
  option: FilterOption;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

function CheckboxRow({ option, checked, onChange }: CheckboxRowProps) {
  return (
    <label className="flex items-center cursor-pointer select-none group">
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="hidden"
      />

      {/* Skewed Checkbox */}
      <span
        className={cn(
          'w-5 h-5 border-2 mr-4 flex items-center justify-center transition-all',
          checked
            ? 'bg-[#FF6B00] border-[#FF6B00]'
            : 'border-[#555555] group-hover:border-[#FF6B00]'
        )}
        style={{ transform: 'skewX(-12deg)' }}
      >
        {checked && (
          <span className="text-black text-xs font-bold" style={{ transform: 'skewX(12deg)' }}>
            ✓
          </span>
        )}
      </span>

      {/* Label */}
      <span className="text-[#A0A0A0] text-sm transition-colors group-hover:text-white">
        {option.label}
        {option.count !== undefined && (
          <span className="text-[#666666] ml-2">({option.count})</span>
        )}
      </span>
    </label>
  );
}

// ============================================
// Exports
// ============================================

export default ElectricSidebar;
