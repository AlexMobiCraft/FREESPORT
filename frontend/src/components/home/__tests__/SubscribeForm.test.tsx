/**
 * Unit tests for SubscribeForm component
 * Story 11.3 - AC 6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SubscribeForm } from '../SubscribeForm';
import { toast } from 'react-hot-toast';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock subscribeService
vi.mock('@/services/subscribeService', () => ({
  subscribeService: {
    subscribe: vi.fn(),
  },
}));

import { subscribeService } from '@/services/subscribeService';

const getPdpCheckbox = () =>
  screen.getByRole('checkbox', { name: /обработку моих персональных данных/i });

const clickPdpCheckbox = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(getPdpCheckbox());
};

const fillEmailAndAcceptConsent = async (
  user: ReturnType<typeof userEvent.setup>,
  email = 'new@example.com'
) => {
  await user.type(screen.getByLabelText(/электронная почта/i), email);
  await clickPdpCheckbox(user);
};

describe('SubscribeForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders subscribe form correctly', () => {
    render(<SubscribeForm />);

    expect(screen.getByText('Подписаться на рассылку')).toBeInTheDocument();
    expect(screen.getByLabelText(/электронная почта/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /подписаться/i })).toBeInTheDocument();
  });

  it('renders PDN checkbox with privacy policy link', () => {
    render(<SubscribeForm />);

    expect(getPdpCheckbox()).toBeInTheDocument();
    const link = screen.getByRole('link', {
      name: /обработку моих персональных данных/i,
    });
    expect(link).toHaveAttribute('href', '/privacy-policy');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(link.closest('label')).toBeNull();
  });

  it('shows validation error for invalid email pattern', async () => {
    const user = userEvent.setup();
    render(<SubscribeForm />);

    const input = screen.getByLabelText(/электронная почта/i);
    const button = screen.getByRole('button', { name: /подписаться/i });

    // Email that passes HTML5 type=email validation but fails our regex pattern
    await user.type(input, 'test@x');
    await clickPdpCheckbox(user);
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByText('Введите корректный email')).toBeInTheDocument();
    });
  });

  it('shows validation error for empty email', async () => {
    const user = userEvent.setup();
    render(<SubscribeForm />);

    const button = screen.getByRole('button', { name: /подписаться/i });
    await clickPdpCheckbox(user);
    await user.click(button);

    await waitFor(() => {
      expect(screen.getByText('Email обязателен')).toBeInTheDocument();
    });
  });

  it('blocks submit without PDN consent', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    const user = userEvent.setup();
    render(<SubscribeForm />);

    await user.type(screen.getByLabelText(/электронная почта/i), 'new@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(screen.getByText('Необходимо согласие на обработку персональных данных')).toBeInTheDocument();
    });
    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('marks PDN checkbox invalid and links error text through aria-describedby', async () => {
    const user = userEvent.setup();
    render(<SubscribeForm />);

    await user.type(screen.getByLabelText(/электронная почта/i), 'new@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    const checkbox = await screen.findByRole('checkbox', {
      name: /обработку моих персональных данных/i,
    });
    const alert = screen.getByRole('alert');
    expect(checkbox).toHaveAttribute('aria-invalid', 'true');
    expect(checkbox).toHaveAttribute('aria-describedby', alert.id);
  });

  it('generates unique PDN ids for multiple form instances', () => {
    render(
      <>
        <SubscribeForm />
        <SubscribeForm />
      </>
    );

    const checkboxes = screen.getAllByRole('checkbox', {
      name: /обработку моих персональных данных/i,
    });
    const checkboxIds = checkboxes.map(checkbox => checkbox.getAttribute('id'));
    expect(new Set(checkboxIds).size).toBe(2);
  });

  it('calls subscribe service with email and PDN consent payload', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockResolvedValueOnce({
      message: 'Successfully subscribed',
      email: 'new@example.com',
    });

    const user = userEvent.setup();
    render(<SubscribeForm />);

    await fillEmailAndAcceptConsent(user, 'new@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith({
        email: 'new@example.com',
        pdp_consent: true,
      });
    });
  });

  it('shows success toast on successful subscription and resets form', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockResolvedValueOnce({
      message: 'Successfully subscribed',
      email: 'new@example.com',
    });

    const user = userEvent.setup();
    render(<SubscribeForm />);

    const input = screen.getByLabelText(/электронная почта/i);
    const button = screen.getByRole('button', { name: /подписаться/i });

    await fillEmailAndAcceptConsent(user, 'new@example.com');
    await user.click(button);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Вы успешно подписались на рассылку');
    });

    expect(input).toHaveValue('');
    expect(getPdpCheckbox()).not.toBeChecked();
  });

  it('shows error toast when email already subscribed', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(new Error('already_subscribed'));

    const user = userEvent.setup();
    render(<SubscribeForm />);

    await fillEmailAndAcceptConsent(user, 'existing@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Этот email уже подписан на рассылку');
    });
  });

  it('shows backend PDN field error instead of email validation fallback', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(
      Object.assign(new Error('validation_error'), {
        details: {
          pdp_consent: ['Необходимо согласие на обработку персональных данных.'],
        },
      })
    );

    const user = userEvent.setup();
    render(<SubscribeForm />);

    await fillEmailAndAcceptConsent(user, 'server-pdp@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(screen.getByText('Необходимо согласие на обработку персональных данных.')).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith(
        'Необходимо согласие на обработку персональных данных.'
      );
    });
  });

  it('shows error toast on network error', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(new Error('network_error'));

    const user = userEvent.setup();
    render(<SubscribeForm />);

    await fillEmailAndAcceptConsent(user, 'test@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Не удалось подписаться. Попробуйте позже');
    });
  });

  it('disables button during submission', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    let resolvePromise: (value: { message: string; email: string }) => void;
    mockSubscribe.mockImplementationOnce(
      () =>
        new Promise(resolve => {
          resolvePromise = resolve;
        })
    );

    const user = userEvent.setup();
    render(<SubscribeForm />);

    const button = screen.getByRole('button', { name: /подписаться/i });

    await fillEmailAndAcceptConsent(user, 'test@example.com');
    await user.click(button);

    // Button should be disabled and show loading text
    expect(button).toBeDisabled();
    expect(screen.getByText('Отправка...')).toBeInTheDocument();

    // Resolve the promise
    resolvePromise!({ message: 'Success', email: 'test@example.com' });

    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });
});
