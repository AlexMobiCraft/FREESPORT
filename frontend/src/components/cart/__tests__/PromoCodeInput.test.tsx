/**
 * PromoCodeInput Component Tests
 *
 * Покрытие:
 * - Рендеринг input и кнопки
 * - Ввод текста в поле промокода
 * - Disabled state кнопки при пустом поле
 * - Loading state при применении
 * - Enter для отправки
 *
 * @see Story 26.3: Cart Summary (placeholder)
 * @see Story 26.4: Promo Code Integration
 */

import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import PromoCodeInput from '../PromoCodeInput';

describe('PromoCodeInput', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ================== Базовый рендеринг ==================
  describe('Rendering', () => {
    it('renders promo code section container', () => {
      render(<PromoCodeInput />);
      expect(screen.getByTestId('promo-code-section')).toBeInTheDocument();
    });

    it('renders promo code input field', () => {
      render(<PromoCodeInput />);
      expect(screen.getByTestId('promo-code-input')).toBeInTheDocument();
    });

    it('renders apply button', () => {
      render(<PromoCodeInput />);
      expect(screen.getByTestId('apply-promo-button')).toBeInTheDocument();
    });

    it('displays placeholder text', () => {
      render(<PromoCodeInput />);
      expect(screen.getByPlaceholderText('Введите промокод')).toBeInTheDocument();
    });

    it('displays "Применить" button text', () => {
      render(<PromoCodeInput />);
      expect(screen.getByText('Применить')).toBeInTheDocument();
    });
  });

  // ================== Input Interaction ==================
  describe('Input Interaction', () => {
    it('updates input value on change', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input') as HTMLInputElement;

      fireEvent.change(input, { target: { value: 'SALE10' } });

      expect(input.value).toBe('SALE10');
    });

    it('clears input value', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input') as HTMLInputElement;

      fireEvent.change(input, { target: { value: 'SALE10' } });
      fireEvent.change(input, { target: { value: '' } });

      expect(input.value).toBe('');
    });
  });

  // ================== Button State ==================
  describe('Button State', () => {
    it('button is disabled when input is empty', () => {
      render(<PromoCodeInput />);
      const button = screen.getByTestId('apply-promo-button');

      expect(button).toBeDisabled();
    });

    it('button is disabled when input contains only whitespace', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');
      const button = screen.getByTestId('apply-promo-button');

      fireEvent.change(input, { target: { value: '   ' } });

      expect(button).toBeDisabled();
    });

    it('button is enabled when input has text', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');
      const button = screen.getByTestId('apply-promo-button');

      fireEvent.change(input, { target: { value: 'SALE10' } });

      expect(button).not.toBeDisabled();
    });
  });

  // ================== Apply Action ==================
  describe('Apply Action', () => {
    it('shows loading state when applying promo', async () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');
      const button = screen.getByTestId('apply-promo-button');

      fireEvent.change(input, { target: { value: 'SALE10' } });
      fireEvent.click(button);

      expect(screen.getByText('Проверка...')).toBeInTheDocument();
      expect(button).toBeDisabled();
    });

    it('returns to normal state after loading', async () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');
      const button = screen.getByTestId('apply-promo-button');

      fireEvent.change(input, { target: { value: 'SALE10' } });
      fireEvent.click(button);

      // Проверяем что показывается loading
      expect(screen.getByText('Проверка...')).toBeInTheDocument();

      // Ждём завершения setTimeout с fake timers
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      // После timeout должен вернуться "Применить"
      expect(screen.getByText('Применить')).toBeInTheDocument();
    });

    it('does not trigger apply when code is empty', () => {
      render(<PromoCodeInput />);
      const button = screen.getByTestId('apply-promo-button');

      fireEvent.click(button);

      // Кнопка disabled, клик не срабатывает
      expect(screen.queryByText('Проверка...')).not.toBeInTheDocument();
    });
  });

  // ================== Keyboard Interaction ==================
  describe('Keyboard Interaction', () => {
    it('triggers apply on Enter key press', async () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');

      fireEvent.change(input, { target: { value: 'SALE10' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(screen.getByText('Проверка...')).toBeInTheDocument();
    });

    it('does not trigger apply on Enter when input is empty', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');

      fireEvent.keyDown(input, { key: 'Enter' });

      expect(screen.queryByText('Проверка...')).not.toBeInTheDocument();
    });

    it('does not trigger apply on other keys', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');

      fireEvent.change(input, { target: { value: 'SALE10' } });
      fireEvent.keyDown(input, { key: 'Escape' });

      expect(screen.queryByText('Проверка...')).not.toBeInTheDocument();
    });
  });

  // ================== Accessibility ==================
  describe('Accessibility', () => {
    it('input has aria-label', () => {
      render(<PromoCodeInput />);
      const input = screen.getByTestId('promo-code-input');

      expect(input).toHaveAttribute('aria-label', 'Промокод');
    });
  });
});
