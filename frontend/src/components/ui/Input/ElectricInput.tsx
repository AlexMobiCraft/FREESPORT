/**
 * Electric Orange Input Component
 *
 * Text input field for Electric Orange design system
 * Features:
 * - Rectangular geometry (NO skew - inputs stay straight)
 * - Dark transparent background
 * - Orange border on focus
 * - Error state with red border
 *
 * @see docs/4-ux-design/00-design-system-migration/02-component-specs.md#input
 */

'use client';

import React, { forwardRef } from 'react';
import { cn } from '@/utils/cn';

// ============================================
// Types
// ============================================

export interface ElectricInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Input size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Error state */
  error?: boolean;
  /** Error message to display */
  errorMessage?: string;
  /** Label for the input */
  label?: string;
  /** Full width mode */
  fullWidth?: boolean;
}

// ============================================
// Size Configurations
// ============================================

const sizeStyles = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-4 text-base',
  lg: 'h-13 px-5 text-lg',
};

// ============================================
// Input Component
// ============================================

export const ElectricInput = forwardRef<HTMLInputElement, ElectricInputProps>(
  (
    { size = 'md', error = false, errorMessage, label, fullWidth = false, className, id, ...props },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className={cn('flex flex-col', fullWidth && 'w-full')}>
        {/* Label */}
        {label && (
          <label
            htmlFor={inputId}
            className="text-[#A0A0A0] text-sm mb-2"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            {label}
          </label>
        )}

        {/* Input */}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            // Base styles - Rectangular, NO skew
            'bg-transparent border text-white',
            'placeholder-[#666666]',
            'transition-all duration-150',
            'outline-none',

            // Size
            sizeStyles[size],

            // States
            error
              ? 'border-[#EF4444] focus:border-[#EF4444] focus:ring-1 focus:ring-[#EF4444]'
              : 'border-[#333333] hover:border-[#444444] focus:border-[#FF6B00] focus:ring-1 focus:ring-[#FF6B00]',

            // Disabled
            'disabled:opacity-50 disabled:cursor-not-allowed',

            // Full width
            fullWidth && 'w-full',

            className
          )}
          style={{ fontFamily: "'Inter', sans-serif" }}
          {...props}
        />

        {/* Error Message */}
        {error && errorMessage && <p className="text-[#EF4444] text-sm mt-1">{errorMessage}</p>}
      </div>
    );
  }
);

ElectricInput.displayName = 'ElectricInput';

export default ElectricInput;
