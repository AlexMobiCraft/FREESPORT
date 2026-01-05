/**
 * Electric Orange Spinner Component
 *
 * Индикатор загрузки в стиле Electric Orange
 * Features:
 * - Skewed square that rotates
 * - Orange primary color
 * - Multiple sizes
 *
 * @see docs/4-ux-design/00-design-system-migration/02-component-specs.md
 */

'use client';

import React from 'react';
import { cn } from '@/utils/cn';

// ============================================
// Types
// ============================================

export type ElectricSpinnerSize = 'sm' | 'md' | 'lg';

export interface ElectricSpinnerProps {
  /** Spinner size */
  size?: ElectricSpinnerSize;
  /** Additional class names */
  className?: string;
}

// ============================================
// Component
// ============================================

const sizeClasses: Record<ElectricSpinnerSize, string> = {
  sm: 'w-5 h-5',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
};

export function ElectricSpinner({ size = 'md', className }: ElectricSpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Загрузка"
      className={cn(
        'inline-block',
        sizeClasses[size],
        'border-2 border-[var(--border-default)] border-t-[var(--color-primary)]',
        'transform -skew-x-12',
        'animate-spin',
        className
      )}
    >
      <span className="sr-only">Загрузка...</span>
    </div>
  );
}

ElectricSpinner.displayName = 'ElectricSpinner';

// ============================================
// Full Page Loading
// ============================================

export interface ElectricLoadingProps {
  /** Loading text */
  text?: string;
  /** Additional class names */
  className?: string;
}

export function ElectricLoading({ text = 'Загрузка...', className }: ElectricLoadingProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-4', className)}>
      <ElectricSpinner size="lg" />
      <span className="text-[var(--color-text-secondary)] text-sm">{text}</span>
    </div>
  );
}

ElectricLoading.displayName = 'ElectricLoading';

export default ElectricSpinner;
