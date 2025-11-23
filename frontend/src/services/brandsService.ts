/**
 * Brands Service - методы для работы с брендами
 */

import apiClient from './api-client';
import type { Brand, PaginatedResponse } from '@/types/api';

class BrandsService {
  async getAll(): Promise<Brand[]> {
    const response = await apiClient.get<PaginatedResponse<Brand>>('/brands/');
    return response.data.results;
  }
}

const brandsService = new BrandsService();
export default brandsService;
