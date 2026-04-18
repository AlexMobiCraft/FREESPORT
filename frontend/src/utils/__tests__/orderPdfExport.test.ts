/**
 * Regression-тесты для утилиты экспорта заказа в PDF (Story 34-2)
 * Проверяет локализацию delivery_method в генерируемом PDF-документе.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Hoisted mocks — доступны внутри vi.mock factory
const mockSave = vi.hoisted(() => vi.fn());
const mockText = vi.hoisted(() => vi.fn());
const mockLine = vi.hoisted(() => vi.fn());

vi.mock('jspdf', () => ({
  jsPDF: function MockJsPDF() {
    return {
      setFontSize: vi.fn(),
      setFont: vi.fn(),
      setLineWidth: vi.fn(),
      setTextColor: vi.fn(),
      text: mockText,
      line: mockLine,
      addPage: vi.fn(),
      save: mockSave,
      internal: { pageSize: { getWidth: () => 210 } },
    };
  },
}));

import { getDeliveryMethodLabel, generateOrderPdf } from '../orderPdfExport';
import type { Order } from '@/types/order';

const baseOrder: Order = {
  id: 1,
  order_number: 'ORD-001',
  user: 1,
  customer_display_name: 'Иван Иванов',
  customer_name: 'Иван Иванов',
  customer_email: 'ivan@example.com',
  customer_phone: '+79001234567',
  status: 'pending',
  total_amount: '5000.00',
  discount_amount: '0.00',
  delivery_cost: '300.00',
  delivery_address: 'г. Москва, ул. Тестовая, д. 1',
  delivery_method: 'courier',
  delivery_date: null,
  tracking_number: '',
  payment_method: 'card',
  payment_status: 'pending',
  payment_id: '',
  notes: '',
  sent_to_1c: false,
  sent_to_1c_at: null,
  status_1c: '',
  is_master: true,
  vat_group: null,
  created_at: '2026-04-18T10:00:00Z',
  updated_at: '2026-04-18T10:00:00Z',
  items: [
    {
      id: 1,
      product: { id: 101, name: 'Тестовый товар' },
      variant: null,
      product_name: 'Тестовый товар',
      product_sku: 'SKU-001',
      variant_info: 'Размер: XL',
      quantity: 2,
      unit_price: '2000.00',
      total_price: '4000.00',
    },
  ],
  subtotal: '4000.00',
  total_items: 1,
  calculated_total: '4300.00',
  can_be_cancelled: true,
};

describe('getDeliveryMethodLabel', () => {
  it('локализует courier', () => {
    expect(getDeliveryMethodLabel('courier')).toBe('Курьерская доставка');
  });

  it('локализует pickup', () => {
    expect(getDeliveryMethodLabel('pickup')).toBe('Самовывоз');
  });

  it('локализует post', () => {
    expect(getDeliveryMethodLabel('post')).toBe('Почтовая доставка');
  });

  it('локализует transport_company (Story 34-2 regression)', () => {
    expect(getDeliveryMethodLabel('transport_company')).toBe('Транспортная компания');
  });

  it('локализует transport_schedule (Story 34-2 regression)', () => {
    expect(getDeliveryMethodLabel('transport_schedule')).toBe('Доставка по расписанию');
  });

  it('возвращает raw code для неизвестного значения', () => {
    expect(getDeliveryMethodLabel('unknown_method')).toBe('unknown_method');
  });
});

describe('generateOrderPdf — delivery_method локализация', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function getTextArgs(): string[] {
    return mockText.mock.calls.map((args: unknown[]) => args[0] as string);
  }

  it('выводит локализованный label для transport_company (Story 34-2 regression)', () => {
    generateOrderPdf({ ...baseOrder, delivery_method: 'transport_company' });
    const allText = getTextArgs().join(' ');
    expect(allText).toContain('Транспортная компания');
    expect(allText).not.toContain('transport_company');
  });

  it('выводит локализованный label для transport_schedule (Story 34-2 regression)', () => {
    generateOrderPdf({ ...baseOrder, delivery_method: 'transport_schedule' });
    const allText = getTextArgs().join(' ');
    expect(allText).toContain('Доставка по расписанию');
    expect(allText).not.toContain('transport_schedule');
  });

  it('выводит локализованный label для courier', () => {
    generateOrderPdf({ ...baseOrder, delivery_method: 'courier' });
    const allText = getTextArgs().join(' ');
    expect(allText).toContain('Курьерская доставка');
  });

  it('вызывает doc.save с именем файла на основе order_number', () => {
    generateOrderPdf(baseOrder);
    expect(mockSave).toHaveBeenCalledWith('order-ORD-001.pdf');
  });
});
