/**
 * Button Component
 * Базовый компонент кнопки согласно FREESPORT Design System
 *
 * @see frontend/docs/design-system.json#components.Button
 */

import React from 'react';
import { cn } from '@/utils/cn';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Вариант кнопки */
  variant?: 'primary' | 'secondary' | 'tertiary' | 'subtle' | 'danger';
  /** Размер кнопки */
  size?: 'small' | 'medium' | 'large';
  /** Состояние загрузки */
  loading?: boolean;
  /** Дочерние элементы */
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'medium',
      loading = false,
      className,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        className={cn(
          // Базовые стили
          'inline-flex items-center justify-center gap-2',
          'font-medium transition-all',
          'focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed',

          // Варианты
          variant === 'primary' && [
            'bg-[var(--color-primary)] text-[var(--color-text-inverse)]',
            'shadow-[var(--shadow-primary)]',
            'hover:bg-[var(--color-primary-hover)] hover:-translate-y-0.5',
            'active:bg-[var(--color-primary-active)] active:translate-y-0',
          ],
          variant === 'secondary' && [
            'bg-[var(--color-neutral-100)] border border-[var(--color-primary)] text-[var(--color-primary)]',
            'shadow-[var(--shadow-default)]',
            'hover:bg-[var(--color-neutral-200)] hover:-translate-y-0.5',
            'active:translate-y-0',
          ],
          variant === 'tertiary' && [
            'bg-transparent text-[var(--color-primary)]',
            'hover:bg-[var(--color-neutral-200)] hover:-translate-y-0.5',
            'active:translate-y-0',
          ],
          variant === 'subtle' && [
            'bg-[#E7F3FF] text-[var(--color-primary)]',
            'shadow-[var(--shadow-default)]',
            'hover:bg-[#D6E9FF] hover:-translate-y-0.5',
            'active:translate-y-0',
          ],
          variant === 'danger' && [
            'bg-[#C23B3B] text-white',
            'shadow-[var(--shadow-primary)]',
            'hover:bg-[#A32F2F] hover:-translate-y-0.5',
            'active:bg-[#8B2828] active:translate-y-0',
            'focus:ring-[#C23B3B]',
          ],

          // Размеры
          size === 'small' && 'h-10 px-6 text-body-s rounded-sm',
          size === 'medium' && 'h-10 px-6 text-body-m rounded-sm',
          size === 'large' && 'h-12 px-8 text-body-l rounded-sm',

          className
        )}
        disabled={isDisabled}
        {...props}
      >
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
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
