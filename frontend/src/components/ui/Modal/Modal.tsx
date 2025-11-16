/**
 * Modal Component
 * Центрированное окно с backdrop blur и управлением фокусом
 *
 * @see frontend/docs/design-system.json#components.Modal
 */

import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface ModalProps {
  /** Открыт ли модал */
  isOpen: boolean;
  /** Callback при закрытии */
  onClose: () => void;
  /** Заголовок */
  title: string;
  /** Контент */
  children: React.ReactNode;
  /** Footer (опционально) */
  footer?: React.ReactNode;
  /** CSS класс для кастомизации */
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedElement = useRef<HTMLElement | null>(null);

  // Edge Case: Предупреждение о вложенных модалах
  useEffect(() => {
    if (isOpen) {
      const existingModals = document.querySelectorAll('[role="dialog"][aria-modal="true"]');
      if (existingModals.length > 0) {
        console.warn(
          'Nested modals are not supported. Close the current modal before opening a new one.'
        );
      }
    }
  }, [isOpen]);

  // Edge Case: Управление фокусом
  useEffect(() => {
    if (!isOpen) return;

    // Сохраняем элемент, который был в фокусе
    previouslyFocusedElement.current = document.activeElement as HTMLElement;

    // Фокус на первый интерактивный элемент
    const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    // Возвращаем фокус при закрытии
    return () => {
      if (previouslyFocusedElement.current) {
        previouslyFocusedElement.current.focus();
      }
    };
  }, [isOpen]);

  // Edge Case: Focus trap (Tab циклически внутри Modal)
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    if (e.key === 'Tab') {
      const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (!focusableElements || focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey) {
        // Shift+Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    }
  };

  // Edge Case: Клик на backdrop закрывает
  const handleBackdropClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      role="presentation"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-primary/50 backdrop-blur-sm" aria-hidden="true" />

      {/* Modal Content */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={cn(
          'relative w-full max-w-[560px] max-h-[80vh]',
          'bg-neutral-100 rounded-xl shadow-modal',
          'flex flex-col',
          className
        )}
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-neutral-300">
          <h2 id="modal-title" className="text-title-m font-semibold text-text-primary pr-8">
            {title}
          </h2>

          {/* Close Button */}
          <button
            onClick={onClose}
            className={cn(
              'flex items-center justify-center',
              'w-11 h-11 rounded-xl',
              'transition-colors duration-short',
              'hover:bg-[#E3E8F2]',
              'focus:outline-none focus:ring-2 focus:ring-primary'
            )}
            aria-label="Закрыть модальное окно"
          >
            <X className="w-10 h-10 text-neutral-700" />
          </button>
        </div>

        {/* Content - Edge Case: Overflow контента > 80vh - добавляем скролл */}
        <div className="flex-1 overflow-y-auto p-6">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="border-t border-neutral-300 p-6 flex items-center justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

Modal.displayName = 'Modal';
