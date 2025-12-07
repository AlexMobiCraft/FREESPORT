/**
 * PromoCodeInput Component - Placeholder для ввода промокода
 *
 * Функции:
 * - Input поле для ввода промокода
 * - Кнопка "Применить" с loading state
 * - Stub логика - будет реализована в Story 26.4
 *
 * @see Story 26.3: Cart Summary (placeholder)
 * @see Story 26.4: Promo Code Integration (полная реализация)
 */
'use client';

import { useState } from 'react';

/**
 * Компонент ввода промокода (placeholder)
 * Полная логика будет реализована в Story 26.4
 */
const PromoCodeInput = () => {
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Обработчик применения промокода
   * TODO: Реализовать валидацию в Story 26.4
   */
  const handleApply = async () => {
    if (!code.trim()) return;

    setIsLoading(true);
    // Placeholder - будет реализовано в Story 26.4
    // TODO: Implement promo code validation via API
    setTimeout(() => setIsLoading(false), 500);
  };

  /**
   * Обработчик нажатия Enter
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && code.trim() && !isLoading) {
      handleApply();
    }
  };

  return (
    <div className="flex gap-2 mb-4" data-testid="promo-code-section">
      <input
        type="text"
        value={code}
        onChange={e => setCode(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите промокод"
        className="flex-1 h-10 px-3 border border-[var(--color-neutral-400)] rounded-[var(--radius-sm)]
                   text-body-m focus:outline-none focus:ring-[var(--focus-ring)] 
                   focus:border-[var(--color-primary)] bg-[var(--bg-panel)]"
        data-testid="promo-code-input"
        aria-label="Промокод"
      />
      <button
        onClick={handleApply}
        disabled={!code.trim() || isLoading}
        className="px-4 h-10 bg-[var(--color-primary-subtle)] text-[var(--color-primary)] 
                   rounded-[var(--radius-sm)] text-body-m font-medium 
                   hover:bg-[var(--color-primary)] hover:text-[var(--color-text-inverse)]
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        data-testid="apply-promo-button"
      >
        {isLoading ? 'Проверка...' : 'Применить'}
      </button>
    </div>
  );
};

export default PromoCodeInput;
