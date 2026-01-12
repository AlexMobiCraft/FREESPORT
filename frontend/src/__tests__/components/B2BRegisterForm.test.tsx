/**
 * B2BRegisterForm Component Tests
 * Story 28.2 - Поток регистрации B2B
 *
 * Tests для компонента формы B2B регистрации
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { B2BRegisterForm } from '@/components/auth/B2BRegisterForm';

// Mock authService
vi.mock('@/services/authService', () => ({
  default: {
    registerB2B: vi.fn(),
  },
}));

// Mock useRouter
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('B2BRegisterForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render all required fields', () => {
      render(<B2BRegisterForm />);

      expect(screen.getByLabelText(/^имя$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/фамилия/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/телефон/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/название компании/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^инн$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^огрн$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/юридический адрес/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^пароль$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/подтверждение пароля/i)).toBeInTheDocument();
    });

    it('should show B2B information panel', () => {
      render(<B2BRegisterForm />);

      expect(screen.getByText(/регистрация для бизнес-партнеров/i)).toBeInTheDocument();
    });

    it('should render submit button', () => {
      render(<B2BRegisterForm />);

      const submitButton = screen.getByRole('button', { name: /отправить заявку/i });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for inputs', () => {
      render(<B2BRegisterForm />);

      // Check specific important inputs have labels
      expect(screen.getByLabelText(/^имя$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^инн$/i)).toBeInTheDocument();
    });
  });
});
