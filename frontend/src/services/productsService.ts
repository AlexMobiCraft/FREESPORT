/**
 * Products Service - методы для работы с товарами
 */

import apiClient from './api-client';
import type { Product, PaginatedResponse } from '@/types/api';

interface ProductFilters {
  page?: number;
  limit?: number;
  category?: string;
  brand?: string;
  min_price?: number;
  max_price?: number;
}

class ProductsService {
  /**
   * Получить список товаров с пагинацией и фильтрами
   */
  async getAll(filters?: ProductFilters): Promise<PaginatedResponse<Product>> {
    const response = await apiClient.get<PaginatedResponse<Product>>('/products/', {
      params: filters,
    });
    return response.data;
  }

  /**
   * Получить товар по ID
   */
  async getById(id: number): Promise<Product> {
    const response = await apiClient.get<Product>(`/products/${id}/`);
    return response.data;
  }

  /**
   * Поиск товаров
   */
  async search(query: string): Promise<{ results: Product[] }> {
    const response = await apiClient.get<{ results: Product[] }>('/products/search/', {
      params: { q: query },
    });
    return response.data;
  }

  /**
   * Фильтрация товаров
   */
  async filter(filters: ProductFilters): Promise<PaginatedResponse<Product>> {
    return this.getAll(filters);
  }
}

const productsService = new ProductsService();
export default productsService;
