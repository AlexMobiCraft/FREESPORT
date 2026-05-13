import { describe, it, expect, vi, beforeEach } from 'vitest';
import { subscribeService } from '../subscribeService';
import apiClient from '../api-client';

vi.mock('../api-client');

describe('subscribeService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts the full subscribe payload', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        message: 'Вы успешно подписались на рассылку',
        email: 'new@example.com',
      },
    });

    await subscribeService.subscribe({
      email: 'new@example.com',
      pdp_consent: true,
    });

    expect(apiClient.post).toHaveBeenCalledWith('/subscribe', {
      email: 'new@example.com',
      pdp_consent: true,
    });
  });

  it('preserves backend field errors for 400 validation responses', async () => {
    const details = {
      pdp_consent: ['Необходимо согласие на обработку персональных данных.'],
    };
    vi.mocked(apiClient.post).mockRejectedValueOnce({
      response: {
        status: 400,
        data: details,
      },
    });

    await expect(
      subscribeService.subscribe({
        email: 'new@example.com',
        pdp_consent: true,
      })
    ).rejects.toMatchObject({
      message: 'validation_error',
      details,
    });
  });
});
