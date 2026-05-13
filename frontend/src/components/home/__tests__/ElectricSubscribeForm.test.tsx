/**
 * Unit tests for ElectricSubscribeForm component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ElectricSubscribeForm } from '../ElectricSubscribeForm';

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
  const label = document.getElementById('electric-subscribe-pdp-consent-label-prefix');
  expect(label).not.toBeNull();
  await user.click(label!);
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
      expect(screen.getByText('Необходимо согласие на обработку персональных данных')).toBeInTheDocument();
    });
    expect(mockSubscribe).not.toHaveBeenCalled();
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
});
