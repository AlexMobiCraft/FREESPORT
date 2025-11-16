/**
 * Orders Service - методы для работы с заказами
 */

import apiClient from './api-client';
import type { Order, PaginatedResponse } from '@/types/api';

interface OrderData {
  delivery_address: string;
  payment_method: string;
  notes?: string;
}

interface OrderFilters {
  page?: number;
  limit?: number;
}

class OrdersService {
  /**
   * Создать новый заказ
   */
  async create(orderData: OrderData): Promise<Order> {
    const response = await apiClient.post<Order>('/orders/', orderData);
    return response.data;
  }

  /**
   * Получить список заказов с пагинацией
   */
  async getAll(filters?: OrderFilters): Promise<PaginatedResponse<Order>> {
    const response = await apiClient.get<PaginatedResponse<Order>>('/orders/', {
      params: filters,
    });
    return response.data;
  }

  /**
   * Получить заказ по ID
   */
  async getById(id: number): Promise<Order> {
    const response = await apiClient.get<Order>(`/orders/${id}/`);
    return response.data;
  }
}

const ordersService = new OrdersService();
export default ordersService;
