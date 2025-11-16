/**
 * SearchField Component
 * Компактное поле поиска с иконкой внутри
 *
 * @see frontend/docs/design-system.json#components.SearchField
 */

import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface SearchFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Callback при изменении значения */
  onSearch?: (value: string) => void;
  /** Минимальная длина запроса */
  minLength?: number;
}

export const SearchField = React.forwardRef<HTMLInputElement, SearchFieldProps>(
  ({ className, placeholder = 'Поиск...', onSearch, minLength = 2, onChange, ...props }, ref) => {
    const [localValue, setLocalValue] = useState('');
    const [showWarning, setShowWarning] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setLocalValue(value);

      // Edge Case: Проверка минимальной длины
      if (value.length > 0 && value.length < minLength) {
        setShowWarning(true);
      } else {
        setShowWarning(false);
        if (onSearch && value.length >= minLength) {
          onSearch(value);
        }
      }

      onChange?.(e);
    };

    return (
      <div className="w-full">
        <div className="relative">
          {/* Search Icon */}
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600">
            <Search className="w-5 h-5" aria-hidden="true" />
          </div>

          {/* Input */}
          <input
            ref={ref}
            type="search"
            className={cn(
              // Базовые стили
              'w-full h-10 pl-10 pr-4 rounded-sm',
              'text-body-m text-text-primary',
              'bg-neutral-100',
              'border border-[#E3E8F2]',
              'transition-colors duration-short',
              'placeholder:text-neutral-500',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary',

              // Warning state
              showWarning && 'border-accent-warning focus:ring-accent-warning',

              className
            )}
            placeholder={placeholder}
            value={localValue}
            onChange={handleChange}
            aria-label="Поиск"
            {...props}
          />
        </div>

        {/* Edge Case: Предупреждение о минимальной длине */}
        {showWarning && (
          <p className="mt-1 text-caption text-accent-warning">
            Введите минимум {minLength} символа
          </p>
        )}
      </div>
    );
  }
);

SearchField.displayName = 'SearchField';
