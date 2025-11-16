/**
 * InfoPanel Component
 * Информационный баннер с иконкой
 *
 * @see frontend/docs/design-system.json#components.InfoPanel
 */

import React, { useState } from 'react';
import { Info, X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface InfoPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Текст сообщения */
  children: React.ReactNode;
  /** Иконка (по умолчанию Info) */
  icon?: React.ReactNode;
  /** Можно ли закрыть панель */
  onDismiss?: () => void;
}

export const InfoPanel = React.forwardRef<HTMLDivElement, InfoPanelProps>(
  ({ children, icon, onDismiss, className, ...props }, ref) => {
    const [isVisible, setIsVisible] = useState(true);

    const handleDismiss = () => {
      setIsVisible(false);
      onDismiss?.();
    };

    if (!isVisible) return null;

    return (
      <div
        ref={ref}
        className={cn(
          // Базовые стили
          'relative',
          'grid grid-cols-[auto_1fr] gap-4',
          'p-5 rounded-md',
          'bg-neutral-100',
          'border border-primary/20',
          // Edge Case: fade-out анимация при закрытии
          'transition-opacity duration-[200ms]',
          !isVisible && 'opacity-0',

          className
        )}
        {...props}
      >
        {/* Icon Container */}
        <div
          className={cn(
            'flex items-start justify-center',
            'w-20 h-20 rounded-xl',
            'bg-[#00B7FF]/16'
          )}
        >
          <div className="w-12 h-12 text-[#00B7FF] flex items-center justify-center mt-1">
            {/* Edge Case: Иконка по умолчанию если не указана */}
            {icon || <Info className="w-full h-full" aria-hidden="true" />}
          </div>
        </div>

        {/* Text Content */}
        <div className="flex-1">
          {/* Edge Case: Текст автоматически переносится на несколько строк */}
          <div className="text-body-m text-text-primary whitespace-normal break-words pr-8">
            {children}
          </div>
        </div>

        {/* Edge Case: Кнопка закрытия (dismissible) */}
        {onDismiss && (
          <button
            onClick={handleDismiss}
            className={cn(
              'absolute top-3 right-3',
              'flex items-center justify-center',
              'w-8 h-8 rounded-lg',
              'transition-colors duration-short',
              'hover:bg-neutral-200',
              'focus:outline-none focus:ring-2 focus:ring-primary'
            )}
            aria-label="Закрыть"
          >
            <X className="w-5 h-5 text-neutral-600" />
          </button>
        )}
      </div>
    );
  }
);

InfoPanel.displayName = 'InfoPanel';
