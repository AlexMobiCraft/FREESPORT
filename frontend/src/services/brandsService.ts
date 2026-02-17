/**
 * Brands Service - методы для работы с брендами
 */

import apiClient from './api-client';
import type { Brand, PaginatedResponse } from '@/types/api';

const DEFAULT_PAGE_SIZE = 100;
const FEATURED_PAGE_SIZE = 20;

class BrandsService {
  async getAll(): Promise<Brand[]> {
    const response = await apiClient.get<PaginatedResponse<Brand>>('/brands/', {
      params: {
        page_size: DEFAULT_PAGE_SIZE,
      },
    });
    return response.data.results;
  }

  async getFeatured(): Promise<Brand[]> {
    const response = await apiClient.get<PaginatedResponse<Brand>>('/brands/', {
      params: {
        is_featured: true,
        page_size: FEATURED_PAGE_SIZE,
      },
    });
    return response.data.results;
  }
}

const brandsService = new BrandsService();
export default brandsService;
