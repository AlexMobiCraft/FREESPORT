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
  ordering?: string;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

class CategoriesService {
  /**
   * Получить список всех категорий
   */
  async getAll(): Promise<Category[]> {
    const response = await apiClient.get<PaginatedResponse<Category>>('/categories/');
    return response.data.results;
  }

  /**
   * Получить иерархию категорий (дерево)
   */
  async getTree(): Promise<CategoryTree[]> {
    const response = await apiClient.get<CategoryTree[] | PaginatedResponse<CategoryTree>>(
      '/categories-tree/'
    );

    if (Array.isArray(response.data)) {
      return response.data;
    }

    return response.data?.results ?? [];
  }

  /**
   * Получить категории с гибкими фильтрами
   * По умолчанию возвращает корневые (parent_id__isnull=true, limit=6)
   * Если передан parent_id, фильтр parent_id__isnull не применяется
   */
  async getCategories(params?: GetCategoriesParams): Promise<Category[]> {
    const defaults: Record<string, unknown> = { limit: 6 };
    // parent_id__isnull только если parent_id не задан явно
    if (!params?.parent_id) {
      defaults.parent_id__isnull = true;
    }

    const response = await apiClient.get<Category[] | PaginatedResponse<Category>>('/categories/', {
      params: { ...defaults, ...params },
    });
    // Handle both array and paginated response formats (for E2E mocks compatibility)
    if (Array.isArray(response.data)) {
      return response.data;
    }
    return response.data?.results ?? [];
  }
}

const categoriesService = new CategoriesService();
export default categoriesService;
