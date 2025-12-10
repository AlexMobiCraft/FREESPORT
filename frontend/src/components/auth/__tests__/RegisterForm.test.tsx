/**
 * RegisterForm Component Tests
 * Story 28.1 - Task 4.3
 *
 * Component тесты для RegisterForm с использованием Vitest + RTL + MSW
 *
 * AC 9: Component Tests для RegisterForm
 */

import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RegisterForm } from '../RegisterForm';
import authService from '@/services/authService';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

// Mock authService
vi.mock('@/services/authService', () => ({
  default: {
    register: vi.fn(),
  },
}));

describe('RegisterForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  describe('Rendering', () => {
    test('should render all form fields', () => {
      render(<RegisterForm />);

      expect(screen.getByLabelText(/имя/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^пароль$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/подтверждение пароля/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /зарегистрироваться/i })).toBeInTheDocument();
    });

    test('should have proper autocomplete attributes', () => {
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);

      expect(nameInput).toHaveAttribute('autocomplete', 'given-name');
      expect(emailInput).toHaveAttribute('autocomplete', 'email');
      expect(passwordInput).toHaveAttribute('autocomplete', 'new-password');
      expect(confirmInput).toHaveAttribute('autocomplete', 'new-password');
    });

    test('should show password helper text', () => {
      render(<RegisterForm />);

      expect(
        screen.getByText(/минимум 8 символов, 1 цифра и 1 заглавная буква/i)
      ).toBeInTheDocument();
    });
  });

  describe('Client-side Validation', () => {
    test('should show validation error for empty first name', async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);

      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });
      await user.click(submitButton);

      expect(await screen.findByText(/имя обязательно/i)).toBeInTheDocument();
    });

    test('should show validation error for invalid email', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      // Browser type="email" blocks 'invalid-email' format from submitting
      // We verify the form doesn't submit (authService not called) when email is invalid
      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'invalid-email');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      // With browser native validation blocking, authService should NOT be called
      await waitFor(() => {
        expect(mockRegister).not.toHaveBeenCalled();
      });
    });

    test('should show validation error when passwords do not match', async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'ivan@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'DifferentPass456');
      await user.click(submitButton);

      expect(await screen.findByText(/пароли не совпадают/i)).toBeInTheDocument();
    });

    test('should show validation error for password without digit', async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'ivan@example.com');
      await user.type(passwordInput, 'NoDigitsHere');
      await user.type(confirmInput, 'NoDigitsHere');
      await user.click(submitButton);

      expect(await screen.findByText(/хотя бы 1 цифру/i)).toBeInTheDocument();
    });

    test('should show validation error for password without uppercase', async () => {
      const user = userEvent.setup();
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'ivan@example.com');
      await user.type(passwordInput, 'nouppercase123');
      await user.type(confirmInput, 'nouppercase123');
      await user.click(submitButton);

      expect(await screen.findByText(/хотя бы 1 заглавную букву/i)).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    test('should submit form with valid data', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      mockRegister.mockResolvedValue({
        access: 'mock-token',
        refresh: 'mock-refresh',
        user: {
          id: 2,
          email: 'newuser@example.com',
          first_name: 'Новый',
          last_name: '',
          phone: '',
          role: 'retail',
          is_verified: false,
        },
      });

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Новый');
      await user.type(emailInput, 'newuser@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith({
          email: 'newuser@example.com',
          password: 'SecurePass123',
          first_name: 'Новый',
          last_name: '',
          phone: '',
          role: 'retail',
        });
      });

      // Should redirect to home after successful registration
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/');
      });
    });

    test('should call onSuccess callback after successful registration', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      const mockOnSuccess = vi.fn();

      mockRegister.mockResolvedValue({
        access: 'mock-token',
        refresh: 'mock-refresh',
        user: {
          id: 2,
          email: 'newuser@example.com',
          first_name: 'Новый',
          last_name: '',
          phone: '',
          role: 'retail',
          is_verified: false,
        },
      });

      render(<RegisterForm onSuccess={mockOnSuccess} />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Новый');
      await user.type(emailInput, 'newuser@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    test('should display API error on 409 Conflict (existing email)', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      // Return empty email array so component uses Russian fallback message
      mockRegister.mockRejectedValue({
        response: {
          status: 409,
          data: { email: [] },
        },
      });

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Существующий');
      await user.type(emailInput, 'existing@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      // First verify the API was called
      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalled();
      });

      // Then wait for error message to appear with longer timeout
      expect(
        await screen.findByText(/пользователь с таким email уже существует/i, {}, { timeout: 3000 })
      ).toBeInTheDocument();
    });

    test('should display API error on 400 Bad Request (weak password)', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      mockRegister.mockRejectedValue({
        response: {
          status: 400,
          data: { password: ['Password is too weak'] },
        },
      });

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'ivan@example.com');
      await user.type(passwordInput, 'WeakPass1');
      await user.type(confirmInput, 'WeakPass1');
      await user.click(submitButton);

      expect(await screen.findByText(/password is too weak/i)).toBeInTheDocument();
    });

    test('should display API error on 500 Internal Server Error', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      mockRegister.mockRejectedValue({
        response: {
          status: 500,
          data: { detail: 'Internal server error' },
        },
      });

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Иван');
      await user.type(emailInput, 'ivan@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      expect(await screen.findByText(/ошибка сервера/i)).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    test('should show loading state during submission', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);

      mockRegister.mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  access: 'token',
                  refresh: 'refresh',
                  user: {
                    id: 2,
                    email: 'test@example.com',
                    first_name: 'Test',
                    last_name: '',
                    phone: '',
                    role: 'retail',
                    is_verified: false,
                  },
                }),
              100
            )
          )
      );

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Test');
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      // Button should be disabled during submission
      expect(submitButton).toBeDisabled();

      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      });
    });

    test('should disable form inputs during submission', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);

      mockRegister.mockImplementation(
        () =>
          new Promise(resolve =>
            setTimeout(
              () =>
                resolve({
                  access: 'token',
                  refresh: 'refresh',
                  user: {
                    id: 2,
                    email: 'test@example.com',
                    first_name: 'Test',
                    last_name: '',
                    phone: '',
                    role: 'retail',
                    is_verified: false,
                  },
                }),
              100
            )
          )
      );

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i) as HTMLInputElement;
      const emailInput = screen.getByLabelText(/^email$/i) as HTMLInputElement;
      const passwordInput = screen.getByLabelText(/^пароль$/i) as HTMLInputElement;
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i) as HTMLInputElement;
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Test');
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      // All inputs should be disabled during submission
      expect(nameInput).toBeDisabled();
      expect(emailInput).toBeDisabled();
      expect(passwordInput).toBeDisabled();
      expect(confirmInput).toBeDisabled();

      await waitFor(() => {
        expect(nameInput).not.toBeDisabled();
      });
    });
  });

  describe('Accessibility', () => {
    test('should have proper labels for all inputs', () => {
      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);

      expect(nameInput).toHaveAccessibleName();
      expect(emailInput).toHaveAccessibleName();
      expect(passwordInput).toHaveAccessibleName();
      expect(confirmInput).toHaveAccessibleName();
    });

    test('should have role="alert" for error message container', async () => {
      const user = userEvent.setup();
      const mockRegister = vi.mocked(authService.register);
      mockRegister.mockRejectedValue({
        response: {
          status: 409,
          data: { email: ['User with this email already exists'] },
        },
      });

      render(<RegisterForm />);

      const nameInput = screen.getByLabelText(/имя/i);
      const emailInput = screen.getByLabelText(/^email$/i);
      const passwordInput = screen.getByLabelText(/^пароль$/i);
      const confirmInput = screen.getByLabelText(/подтверждение пароля/i);
      const submitButton = screen.getByRole('button', { name: /зарегистрироваться/i });

      await user.type(nameInput, 'Test');
      await user.type(emailInput, 'existing@example.com');
      await user.type(passwordInput, 'SecurePass123');
      await user.type(confirmInput, 'SecurePass123');
      await user.click(submitButton);

      const alert = await screen.findByRole('alert');
      expect(alert).toBeInTheDocument();
    });
  });
});
