/**
 * Badge Component
 * Бейдж для карточек товаров с различными статусами
 *
 * @see frontend/docs/design-system.json#components.Badge
 */

import React from 'react';
import { CheckCircle2, Truck, X, Sparkles } from 'lucide-react';
import { cn } from '@/utils/cn';

export type BadgeVariant =
  | 'delivered'
  | 'transit'
  | 'cancelled'
  | 'promo'
  | 'sale'
  | 'discount'
  | 'premium'
  | 'new'
  | 'hit';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Вариант бейджа */
  variant: BadgeVariant;
  /** Текст */
  children: React.ReactNode;
}

const variantConfig: Record<BadgeVariant, { bg: string; text: string; icon?: React.ReactNode }> = {
  delivered: {
    bg: 'bg-[#E0F5E0]',
    text: 'text-[#1F7A1F]',
    icon: <CheckCircle2 className="w-4 h-4" aria-hidden="true" />,
  },
  transit: {
    bg: 'bg-[#FFF1CC]',
    text: 'text-[#B07600]',
    icon: <Truck className="w-4 h-4" aria-hidden="true" />,
  },
  cancelled: {
    bg: 'bg-[#FFE1E1]',
    text: 'text-[#C23B3B]',
    icon: <X className="w-4 h-4" aria-hidden="true" />,
  },
  promo: { bg: 'bg-[#F4EBDC]', text: 'text-[#8C4C00]' },
  sale: { bg: 'bg-[#F9E1E1]', text: 'text-[#A63232]' },
  discount: { bg: 'bg-[#F4E9FF]', text: 'text-[#5E32A1]' },
  premium: {
    bg: 'bg-[#F6F0E4]',
    text: 'text-[#6D4C1F]',
    icon: <Sparkles className="w-4 h-4" aria-hidden="true" />,
  },
  new: { bg: 'bg-[#E1F0FF]', text: 'text-[#0F5DA3]' },
  hit: { bg: 'bg-[#E3F6EC]', text: 'text-[#1F7A4A]' },
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant, children, className, ...props }, ref) => {
    const config = variantConfig[variant];

    return (
      <span
        ref={ref}
        className={cn(
          // Базовые стили
          'inline-flex items-center gap-1',
          'px-3 py-1 rounded-full',
          'text-caption font-medium',
          // Edge Case: Переполнение текста - max 200px
          'max-w-[200px] truncate',

          // Вариант
          config.bg,
          config.text,

          className
        )}
        {...props}
      >
        {/* Edge Case: Иконка может не загрузиться - показываем только текст */}
        {config.icon}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';
