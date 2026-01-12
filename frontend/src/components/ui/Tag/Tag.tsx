/**
 * Tag Component
 * Компактный label с разными статусами
 *
 * @see frontend/docs/design-system.json#components.Tag
 */

import React from 'react';
import { cn } from '@/utils/cn';

export type TagVariant = 'default' | 'highlight' | 'success' | 'warning' | 'danger';

export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Вариант тега */
  variant?: TagVariant;
  /** Текст */
  children: React.ReactNode;
}

const variantConfig: Record<TagVariant, { bg: string; text: string }> = {
  default: { bg: 'bg-neutral-200', text: 'text-text-secondary' },
  highlight: { bg: 'bg-[#E7F3FF]', text: 'text-[#0060FF]' },
  success: { bg: 'bg-[#E0F5E0]', text: 'text-[#1F7A1F]' },
  warning: { bg: 'bg-[#FFF1CC]', text: 'text-[#B07600]' },
  danger: { bg: 'bg-[#FFE1E1]', text: 'text-[#C23B3B]' },
};

export const Tag = React.forwardRef<HTMLSpanElement, TagProps>(
  ({ variant = 'default', children, className, ...props }, ref) => {
    const config = variantConfig[variant];

    return (
      <span
        ref={ref}
        className={cn(
          // Базовые стили
          'inline-flex items-center',
          'px-2 py-1 rounded-xl',
          'text-caption font-medium',
          // Edge Case: Переполнение текста - max 200px, single-line
          'max-w-[200px] truncate whitespace-nowrap',

          // Вариант
          config.bg,
          config.text,

          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Tag.displayName = 'Tag';
