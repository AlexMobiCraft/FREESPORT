/**
 * Subscribe Service
 * API клиент для подписки на рассылку
 */

import apiClient from './api-client';
import type { SubscribeRequest, SubscribeResponse } from '@/types/api';

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
        const axiosError = error as { response?: { status?: number } };
        if (axiosError.response?.status === 409) {
          throw new Error('already_subscribed');
        }
        if (axiosError.response?.status === 400) {
          throw new Error('validation_error');
        }
      }
      throw new Error('network_error');
    }
  },
};
