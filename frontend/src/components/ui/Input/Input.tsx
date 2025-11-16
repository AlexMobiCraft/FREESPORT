/**
 * Input Component
 * Текстовое поле с поддержкой label, helper, error/success состояний
 *
 * @see frontend/docs/design-system.json#components.Input
 */

import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Метка поля */
  label: string;
  /** Текст подсказки */
  helper?: string;
  /** Сообщение об ошибке */
  error?: string;
  /** Сообщение об успехе */
  success?: string;
  /** Иконка слева */
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    { label, helper, error, success, icon, className, disabled, id, type = 'text', ...props },
    ref
  ) => {
    // Edge Case: Если переданы одновременно error и success - приоритет у error
    const hasError = Boolean(error);
    const hasSuccess = Boolean(success) && !hasError;

    const inputId = id || `input-${label.toLowerCase().replace(/\s+/g, '-')}`;

    return (
      <div className="w-full">
        {/* Label */}
        <label
          htmlFor={inputId}
          className={cn(
            'block text-body-s font-medium text-text-primary mb-1',
            // Edge Case: Label длиннее 50 символов - перенос
            label.length > 50 && 'whitespace-normal break-words'
          )}
        >
          {label}
        </label>

        {/* Input Container */}
        <div className="relative">
          {/* Icon (если передан) */}
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600 w-5 h-5 flex items-center justify-center">
              {icon}
            </div>
          )}

          {/* Input */}
          <input
            ref={ref}
            id={inputId}
            type={type}
            className={cn(
              // Базовые стили
              'w-full h-10 px-4 rounded-sm',
              'text-body-m text-text-primary',
              'bg-neutral-100',
              'border border-neutral-400',
              'transition-colors duration-short',
              'placeholder:text-neutral-500 placeholder:truncate',
              'focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary',

              // Edge Case: Иконка слева - добавляем отступ
              icon && 'pl-10',

              // Состояния
              hasError && [
                'border-accent-danger',
                'bg-accent-danger/8',
                'focus:ring-accent-danger focus:border-accent-danger',
              ],
              hasSuccess && [
                'border-accent-success',
                'focus:ring-accent-success focus:border-accent-success',
              ],

              // Disabled
              disabled && 'opacity-50 cursor-not-allowed bg-neutral-200',

              className
            )}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={
              hasError || hasSuccess || helper ? `${inputId}-description` : undefined
            }
            {...props}
          />

          {/* Error/Success Icons (справа) */}
          {(hasError || hasSuccess) && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              {hasError && (
                <AlertCircle className="w-5 h-5 text-accent-danger" aria-hidden="true" />
              )}
              {hasSuccess && (
                <CheckCircle2 className="w-5 h-5 text-accent-success" aria-hidden="true" />
              )}
            </div>
          )}
        </div>

        {/* Helper/Error/Success Text */}
        {(helper || error || success) && (
          <p
            id={`${inputId}-description`}
            className={cn(
              'mt-1 text-caption',
              // Edge Case: Текст длиннее 100 символов - перенос на несколько строк
              (helper && helper.length > 100) ||
                (error && error.length > 100) ||
                (success && success.length > 100)
                ? 'whitespace-normal break-words'
                : '',
              hasError && 'text-accent-danger',
              hasSuccess && 'text-accent-success',
              !hasError && !hasSuccess && 'text-text-muted'
            )}
          >
            {error || success || helper}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
