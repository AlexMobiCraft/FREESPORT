/**
 * Electric Orange Button Component
 *
 * Button component with Electric Orange Design System styling:
 * - Skewed container (-12deg)
 * - Counter-skewed text (12deg)
 * - Glow-based hover effects
 * - Dark theme optimized
 *
 * @see docs/4-ux-design/00-design-system-migration/02-component-specs.md#button
 */

import React from 'react';
import { cn } from '@/utils/cn';

export interface ElectricButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Вариант кнопки */
  variant?: 'primary' | 'outline' | 'ghost' | 'danger';
  /** Размер кнопки */
  size?: 'sm' | 'md' | 'lg';
  /** Состояние загрузки */
  loading?: boolean;
  /** Полная ширина */
  fullWidth?: boolean;
  /** Дочерние элементы */
  children: React.ReactNode;
}

/**
 * Electric Orange Button
 *
 * Features:
 * - Skewed geometry (-12deg)
 * - Counter-skewed text for readability
 * - Glow effects on hover
 * - Supports primary, outline, ghost variants
 */
export const ElectricButton = React.forwardRef<HTMLButtonElement, ElectricButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      fullWidth = false,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    // Base styles - skewed container
    const baseStyles = [
      'inline-flex items-center justify-center',
      'font-semibold uppercase tracking-wide',
      'transition-all duration-300 ease-out',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#FF6B00] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0F0F0F]',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none',
      // Skew the container
      'transform -skew-x-12',
    ];

    // Variant styles
    const variantStyles = {
      primary: [
        'bg-[#FF6B00] text-black',
        'hover:bg-[#FF8533]',
        'hover:shadow-[0_0_20px_rgba(255,107,0,0.4)]',
        'active:bg-[#E55A00]',
      ],
      outline: [
        'bg-transparent text-white',
        'border-2 border-white',
        'hover:border-[#FF6B00] hover:text-[#FF6B00]',
      ],
      ghost: [
        'bg-transparent text-white',
        'hover:text-[#FF6B00]',
        'hover:bg-[rgba(255,107,0,0.1)]',
      ],
      danger: [
        'bg-[#EF4444] text-white',
        'hover:bg-[#DC2626]',
        'hover:shadow-[0_0_20px_rgba(239,68,68,0.4)]',
        'active:bg-[#B91C1C]',
      ],
    };

    // Size styles
    const sizeStyles = {
      sm: 'h-9 px-4 text-sm gap-2',
      md: 'h-11 px-6 text-base gap-2',
      lg: 'h-14 px-8 text-lg gap-3',
    };

    return (
      <button
        ref={ref}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        disabled={isDisabled}
        {...props}
      >
        {/* Counter-skew wrapper for text */}
        <span className="transform skew-x-12 inline-flex items-center gap-2">
          {loading && (
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          )}
          {children}
        </span>
      </button>
    );
  }
);

ElectricButton.displayName = 'ElectricButton';

export default ElectricButton;
