/**
 * Products Service - методы для работы с товарами
 */

import apiClient from './api-client';
import type { Product, PaginatedResponse } from '@/types/api';

interface ProductFilters {
  page?: number;
  page_size?: number;
  limit?: number;
  category?: string;
  brand?: string;
  min_price?: number;
  max_price?: number;
  ordering?: string;
  in_stock?: boolean;
  is_hit?: boolean;
  is_new?: boolean;
  is_sale?: boolean;
  is_promo?: boolean;
  is_premium?: boolean;
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

  /**
   * Получить хиты продаж (Story 11.2)
   * GET /products?is_hit=true&ordering=-created_at&page_size=8
   */
  async getHits(params?: Partial<ProductFilters>): Promise<Product[]> {
    const response = await apiClient.get<PaginatedResponse<Product>>('/products/', {
      params: {
        is_hit: true,
        ordering: '-created_at',
        page_size: 8,
        in_stock: true,
        ...params,
      },
    });
    return response.data.results;
  }

  /**
   * Получить новинки (Story 11.2)
   * GET /products?is_new=true&ordering=-created_at&page_size=8
   */
  async getNew(params?: Partial<ProductFilters>): Promise<Product[]> {
    const response = await apiClient.get<PaginatedResponse<Product>>('/products/', {
      params: {
        is_new: true,
        ordering: '-created_at',
        page_size: 8,
        in_stock: true,
        ...params,
      },
    });
    return response.data.results;
  }
}

const productsService = new ProductsService();
export default productsService;
