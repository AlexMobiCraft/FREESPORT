/**
 * Banners Service - методы для работы с баннерами
 */

import apiClient from './api-client';
import type { Banner, BannerType } from '@/types/banners';

class BannersService {
  /**
   * Получить активные баннеры для текущего пользователя
   * API автоматически фильтрует по роли из JWT токена
   * @param type - Тип баннера: 'hero' (default) или 'marketing'
   * @returns Массив активных баннеров
   */
  async getActive(type?: BannerType): Promise<Banner[]> {
    const params = type ? { type } : {};
    const response = await apiClient.get<Banner[]>('/banners/', { params });
    return response.data;
  }
}

const bannersService = new BannersService();
export default bannersService;
