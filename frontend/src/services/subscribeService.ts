/**
 * Subscribe Service
 * API клиент для подписки на рассылку
 */

import apiClient from './api-client';
import type { SubscribeRequest, SubscribeResponse } from '@/types/api';

export type SubscribeValidationDetails = Partial<Record<'email' | 'pdp_consent', string[]>>;

export class SubscribeServiceError extends Error {
  details?: SubscribeValidationDetails;

  constructor(message: string, details?: SubscribeValidationDetails) {
    super(message);
    this.name = 'SubscribeServiceError';
    this.details = details;
  }
}

export const subscribeService = {
  /**
   * Подписаться на email-рассылку
   */
  async subscribe(payload: SubscribeRequest): Promise<SubscribeResponse> {
    try {
      const { data } = await apiClient.post<SubscribeResponse>('/subscribe', payload);
      return data;
    } catch (error: unknown) {
      // Проброс ошибки для обработки в компоненте
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as {
          response?: { status?: number; data?: SubscribeValidationDetails };
        };
        if (axiosError.response?.status === 409) {
          throw new SubscribeServiceError('already_subscribed', axiosError.response.data);
        }
        if (axiosError.response?.status === 400) {
          throw new SubscribeServiceError('validation_error', axiosError.response.data);
        }
      }
      throw new SubscribeServiceError('network_error');
    }
  },
};
