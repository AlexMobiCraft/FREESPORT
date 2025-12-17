/**
 * SearchField Component
 * Компактное поле поиска с иконкой внутри
 *
 * @see frontend/docs/design-system.json#components.SearchField
 */

'use client';

import React, { useState, useRef, useEffect, useId } from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface SearchFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Callback при изменении значения */
  onSearch?: (value: string) => void;
  /** Минимальная длина запроса */
  minLength?: number;
  /** Suggestions для автодополнения */
  suggestions?: string[];
  /** Товары для автодополнения */
  products?: Array<{ id: number; name: string; price: number }>;
  /** Debounce delay в миллисекундах */
  debounceMs?: number;
}

export const SearchField = React.forwardRef<HTMLInputElement, SearchFieldProps>(
  (
    {
      className,
      placeholder = 'Поиск',
      onSearch,
      minLength = 2,
      suggestions = [],
      products = [],
      debounceMs = 300,
      onChange,
      ...props
    },
    ref
  ) => {
    const [localValue, setLocalValue] = useState('');
    const [showWarning, setShowWarning] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [debouncedValue, setDebouncedValue] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);
    const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    const listboxId = useId();

    // Debounce effect
    useEffect(() => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        setDebouncedValue(localValue);
        if (onSearch && localValue.length >= minLength) {
          onSearch(localValue);
        }
      }, debounceMs);

      return () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
      };
    }, [localValue, debounceMs, minLength, onSearch]);

    // Close dropdown on click outside
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
          setIsOpen(false);
        }
      };

      if (isOpen) {
        document.addEventListener('mousedown', handleClickOutside);
      }

      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [isOpen]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setLocalValue(value);

      // Показываем dropdown если есть значение
      setIsOpen(value.length > 0);

      // Edge Case: Проверка минимальной длины
      if (value.length > 0 && value.length < minLength) {
        setShowWarning(true);
      } else {
        setShowWarning(false);
      }

      onChange?.(e);
    };

    const handleClear = () => {
      setLocalValue('');
      setDebouncedValue('');
      setIsOpen(false);
      setShowWarning(false);
      if (onSearch) {
        onSearch('');
      }
    };

    const hasResults =
      (suggestions.length > 0 || products.length > 0) && debouncedValue.length >= minLength;

    return (
      <div ref={containerRef} className="w-full relative">
        <div className="relative">
          {/* Search Icon */}
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600">
            <Search className="w-5 h-5" aria-hidden="true" />
          </div>

          {/* Input */}
          <input
            ref={ref}
            type="text"
            role="combobox"
            aria-expanded={isOpen && hasResults}
            aria-controls={isOpen && hasResults ? listboxId : undefined}
            aria-autocomplete="list"
            className={cn(
              // Базовые стили - Design System v2.0
              'w-full h-10 pl-10 pr-10 rounded-md', // 40px height, 6px radius
              'text-body-m text-text-primary',
              'bg-white',
              'border border-[#E3E8F2]', // Design System v2.0 border
              'transition-colors duration-[180ms]',
              'placeholder:text-[#7A7A7A]',
              'focus:outline-none focus:border-[#0060FF] focus:border-[1.5px]', // Design System v2.0 focus

              // Warning state
              showWarning && 'border-accent-warning focus:border-accent-warning',

              className
            )}
            placeholder={placeholder}
            value={localValue}
            onChange={handleChange}
            aria-label="Поиск"
            {...props}
          />

          {/* Clear Button - Design System v2.0 */}
          {localValue.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className={cn(
                'absolute right-3 top-1/2 -translate-y-1/2',
                'w-5 h-5 rounded-full',
                'flex items-center justify-center',
                'text-[#7A7A7A]',
                'hover:bg-[#F5F7FA]',
                'transition-colors duration-[120ms]',
                'focus:outline-none focus:ring-2 focus:ring-[#0060FF]'
              )}
              aria-label="Очистить поиск"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Autocomplete Dropdown - Design System v2.0 */}
        {isOpen && hasResults && (
          <div
            role="listbox"
            id={listboxId}
            className={cn(
              // Позиционирование
              'absolute top-full left-0 right-0 mt-1 z-50',

              // Стили - Design System v2.0
              'bg-white rounded-md',
              'border border-[#E3E8F2]',
              'shadow-lg',

              // Скролл
              'max-h-80 overflow-y-auto',

              // Анимация
              'animate-in fade-in-0 zoom-in-95 duration-100'
            )}
          >
            {/* Suggestions Section */}
            {suggestions.length > 0 && (
              <div className="py-2">
                <div className="px-4 py-1 text-caption text-text-muted font-medium">
                  Популярные запросы
                </div>
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    type="button"
                    role="option"
                    aria-selected={localValue === suggestion}
                    onClick={() => {
                      setLocalValue(suggestion);
                      setIsOpen(false);
                      if (onSearch) {
                        onSearch(suggestion);
                      }
                    }}
                    className={cn(
                      'w-full px-4 py-2 text-left',
                      'flex items-center gap-2',
                      'text-body-m text-text-primary',
                      'hover:bg-[#F5F7FA]',
                      'transition-colors duration-[120ms]'
                    )}
                  >
                    <Search className="w-4 h-4 text-[#7A7A7A]" />
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Products Section */}
            {products.length > 0 && (
              <div className="py-2 border-t border-[#E3E8F2]">
                <div className="px-4 py-1 text-caption text-text-muted font-medium">Товары</div>
                {products.map(product => (
                  <button
                    key={product.id}
                    type="button"
                    role="option"
                    aria-selected={localValue === product.name}
                    onClick={() => {
                      // Handle product selection
                      setIsOpen(false);
                    }}
                    className={cn(
                      'w-full px-4 py-2 text-left',
                      'flex items-center justify-between gap-2',
                      'text-body-m',
                      'hover:bg-[#F5F7FA]',
                      'transition-colors duration-[120ms]'
                    )}
                  >
                    <span className="truncate text-text-primary">{product.name}</span>
                    <span className="text-text-secondary font-medium flex-shrink-0">
                      {product.price.toLocaleString('ru-RU')} ₽
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

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
