/**
 * News Service
 * API клиент для получения новостей
 */

import apiClient from './api-client';
import type { NewsList, NewsItem } from '@/types/api';

interface GetNewsParams {
  page_size?: number;
  page?: number;
}

export const newsService = {
  /**
   * Получить список новостей
   */
  async getNews(params?: GetNewsParams): Promise<NewsItem[]> {
    const { data } = await apiClient.get<NewsList>('/news', {
      params: {
        page_size: 3,
        ...params,
      },
    });
    return data.results;
  },
};
