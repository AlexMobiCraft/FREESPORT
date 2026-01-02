/**
 * Electric Orange Badge Component
 *
 * Skewed badge for product labels, notifications, tags
 * Features:
 * - Skewed geometry (-12deg)
 * - Counter-skewed text (12deg)
 * - Multiple variants (primary, sale, new, hit)
 *
 * @see docs/4-ux-design/00-design-system-migration/02-component-specs.md#badge
 */

'use client';

import React from 'react';
import { cn } from '@/utils/cn';

// ============================================
// Types
// ============================================

export interface ElectricBadgeProps {
  /** Badge variant */
  variant?: 'primary' | 'sale' | 'new' | 'hit' | 'outline';
  /** Badge size */
  size?: 'sm' | 'md';
  /** Badge content */
  children: React.ReactNode;
  /** Additional class names */
  className?: string;
}

// ============================================
// Variant Styles
// ============================================

const variantStyles = {
  primary: 'bg-[#FF6B00] text-black',
  sale: 'bg-[#EF4444] text-white',
  new: 'bg-white text-black',
  hit: 'bg-[#22C55E] text-black',
  outline: 'bg-transparent border-2 border-[#FF6B00] text-[#FF6B00]',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-3 py-1 text-xs',
};

// ============================================
// Badge Component
// ============================================

export function ElectricBadge({
  variant = 'primary',
  size = 'md',
  children,
  className,
}: ElectricBadgeProps) {
  return (
    <span
      className={cn(
        // Base styles
        'inline-flex items-center font-bold uppercase tracking-wider',

        // Variant
        variantStyles[variant],

        // Size
        sizeStyles[size],

        className
      )}
      style={{
        fontFamily: "'Roboto Condensed', sans-serif",
        transform: 'skewX(-12deg)',
      }}
    >
      <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{children}</span>
    </span>
  );
}

export default ElectricBadge;
