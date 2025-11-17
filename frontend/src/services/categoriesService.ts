/**
 * Categories Service - методы для работы с категориями
 */

import apiClient from './api-client';
import type { Category, CategoryTree } from '@/types/api';

interface GetCategoriesParams {
  parent_id?: number | null;
  parent_id__isnull?: boolean;
  level?: number;
  limit?: number;
}

class CategoriesService {
  /**
   * Получить список всех категорий
   */
  async getAll(): Promise<Category[]> {
    const response = await apiClient.get<Category[]>('/categories/');
    return response.data;
  }

  /**
   * Получить иерархию категорий (дерево)
   */
  async getTree(): Promise<CategoryTree[]> {
    const response = await apiClient.get<CategoryTree[]>('/categories/tree/');
    return response.data;
  }

  /**
   * Получить корневые категории для главной страницы (Story 11.2)
   * GET /categories?parent_id__isnull=true&limit=6
   */
  async getCategories(params?: GetCategoriesParams): Promise<Category[]> {
    const response = await apiClient.get<Category[]>('/categories/', {
      params: {
        parent_id__isnull: true, // Django filter: только корневые категории
        limit: 6, // AC 3: до 6 категорий
        ...params,
      },
    });
    return response.data;
  }
}

const categoriesService = new CategoriesService();
export default categoriesService;
