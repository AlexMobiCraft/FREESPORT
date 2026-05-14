/**
 * Unit tests for ElectricSubscribeForm component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ElectricSubscribeForm } from '../ElectricSubscribeForm';
import { toast } from 'react-hot-toast';

vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

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

describe('ElectricSubscribeForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders PDN checkbox with privacy policy link', () => {
    render(<ElectricSubscribeForm />);

    expect(getPdpCheckbox()).toBeInTheDocument();
    const link = screen.getByRole('link', {
      name: /обработку моих персональных данных/i,
    });
    expect(link).toHaveAttribute('href', '/privacy-policy');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(link.closest('label')).toBeNull();
  });

  it('blocks submit without PDN consent', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric@example.com');
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(
        screen.getByText('Необходимо согласие на обработку персональных данных.')
      ).toBeInTheDocument();
    });
    expect(mockSubscribe).not.toHaveBeenCalled();
  });

  it('marks PDN checkbox invalid and links error text through aria-describedby', async () => {
    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric@example.com');
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
        <ElectricSubscribeForm />
        <ElectricSubscribeForm />
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
      email: 'electric@example.com',
    });

    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric@example.com');
    await clickPdpCheckbox(user);
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith({
        email: 'electric@example.com',
        pdp_consent: true,
      });
    });
  });

  it('shows backend PDN field error instead of generic subscription error', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(
      Object.assign(new Error('validation_error'), {
        details: {
          pdp_consent: ['Необходимо согласие на обработку персональных данных.'],
        },
      })
    );

    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric-pdp@example.com');
    await clickPdpCheckbox(user);
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(screen.getByText('Необходимо согласие на обработку персональных данных.')).toBeInTheDocument();
      expect(toast.error).toHaveBeenCalledWith(
        'Необходимо согласие на обработку персональных данных.',
        expect.objectContaining({
          style: expect.objectContaining({ borderRadius: '0' }),
        })
      );
    });
  });

  it('shows unknown backend validation details instead of generic subscription fallback', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(
      Object.assign(new Error('validation_error'), {
        details: {
          non_field_errors: ['Не удалось сохранить согласие. Попробуйте позже.'],
        },
      })
    );

    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric-detail@example.com');
    await clickPdpCheckbox(user);
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Не удалось сохранить согласие. Попробуйте позже.',
        expect.objectContaining({
          style: expect.objectContaining({ borderRadius: '0' }),
        })
      );
    });
  });

  it('shows throttling message on 429 subscribe errors', async () => {
    const mockSubscribe = vi.mocked(subscribeService.subscribe);
    mockSubscribe.mockRejectedValueOnce(new Error('throttled'));

    const user = userEvent.setup();
    render(<ElectricSubscribeForm />);

    await user.type(screen.getByLabelText(/email/i), 'electric-throttled@example.com');
    await clickPdpCheckbox(user);
    await user.click(screen.getByRole('button', { name: /подписаться/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'СЛИШКОМ МНОГО ПОПЫТОК. ПОПРОБУЙТЕ ЧЕРЕЗ МИНУТУ',
        expect.objectContaining({
          style: expect.objectContaining({ borderRadius: '0' }),
        })
      );
    });
  });
});
