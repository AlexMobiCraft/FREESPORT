/**
 * Categories Service - методы для работы с категориями
 */

import apiClient from './api-client';
import type { Category, CategoryTree } from '@/types/api';

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
}

const categoriesService = new CategoriesService();
export default categoriesService;
