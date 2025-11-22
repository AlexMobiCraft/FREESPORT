/**
 * API Types для FREESPORT Frontend
 *
 * Кастомные TypeScript типы для работы с API
 * Дополняют auto-generated типы из api.generated.ts
 */

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role:
    | 'retail'
    | 'wholesale_level1'
    | 'wholesale_level2'
    | 'wholesale_level3'
    | 'trainer'
    | 'federation_rep'
    | 'admin';
  company_name?: string;
  tax_id?: string;
  is_verified?: boolean;
}

export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string;
  retail_price: number;
  opt1_price?: number;
  opt2_price?: number;
  opt3_price?: number;
  is_in_stock: boolean;
  stock_quantity?: number;
  /** Основное изображение, возвращаемое списочным API */
  main_image?: string | null;
  /** Совместимость с ранними моками */
  image?: string | null;
  category: {
    id: number;
    name: string;
    slug: string;
  };
  brand?: {
    id: number;
    name: string;
  };
  images?: Array<{
    id: number;
    image: string;
    is_primary: boolean;
  }>;
  /** Признак доступности к заказу (backend field) */
  can_be_ordered?: boolean;

  // Story 11.0: Маркетинговые флаги для бейджей
  is_hit: boolean;
  is_new: boolean;
  is_sale: boolean;
  is_promo: boolean;
  is_premium: boolean;
  discount_percent: number | null;
}

export interface CartItem {
  id: number;
  product: {
    id: number;
    name: string;
    slug: string;
    retail_price: number;
    opt1_price?: number;
    is_in_stock: boolean;
  };
  quantity: number;
  price: number;
}

export interface Cart {
  id: number;
  items: CartItem[];
  total_amount: number;
  promo_code?: string;
  discount_amount?: number;
}

export interface Order {
  id: number;
  order_number: string;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  items: Array<{
    id: number;
    product_snapshot: {
      name: string;
      price: number;
    };
    quantity: number;
    price: number;
  }>;
  total_amount: number;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  level: number;
  icon: string | null;
  products_count: number;
  description?: string;
}

export interface CategoryTree extends Category {
  children?: CategoryTree[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone: string;
  role?: string;
  company_name?: string;
  tax_id?: string;
}

export interface RegisterResponse {
  user: User;
  access: string;
  refresh: string;
}

export interface RefreshTokenRequest {
  refresh: string;
}

export interface RefreshTokenResponse {
  access: string;
}

export interface ApiError {
  detail?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

// Newsletter Subscription Types
export interface SubscribeRequest {
  email: string;
}

export interface SubscribeResponse {
  message: string;
  email: string;
}

export interface SubscribeError {
  error: string;
  field?: string;
  email?: string;
}

// News Types
export interface NewsItem {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  content?: string;
  image: string | null;
  published_at: string;
  created_at: string;
  updated_at: string;
  author?: string;
  category?: string;
}

export interface NewsList {
  count: number;
  next: string | null;
  previous: string | null;
  results: NewsItem[];
}
