/**
 * Product Detail Page (Story 12.1, 13.5b)
 * SSR страница детального просмотра товара
 * Интегрирует ProductOptions с ProductGallery и ProductSummary
 *
 * @see docs/stories/epic-13/13.5b.productoptions-api-integration.md
 */

import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { cookies } from 'next/headers';
import productsService from '@/services/productsService';
import ProductBreadcrumbs from '@/components/product/ProductBreadcrumbs';
import ProductPageClient from '@/components/product/ProductPageClient';
import type { UserRole } from '@/utils/pricing';

interface ProductPageProps {
  params: {
    slug: string;
  };
}

/**
 * Получает роль пользователя из backend API
 * Fallback на 'guest' если не авторизован
 */
export async function getUserRole(): Promise<UserRole> {
  try {
    const cookieStore = await cookies();
    const sessionId = cookieStore.get('sessionid')?.value || cookieStore.get('fs_session')?.value;

    if (!sessionId) {
      return 'guest';
    }

    // Серверный вызов к backend API для получения профиля пользователя
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    const response = await fetch(`${apiUrl}/api/v1/users/profile/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Cookie: `sessionid=${sessionId}`,
      },
      credentials: 'include',
      cache: 'no-store', // Не кэшируем профиль для актуальности роли
    });

    if (!response.ok) {
      // При ошибке (401, 403, 500) возвращаем guest
      console.warn(`Failed to fetch user profile: ${response.status}`);
      return 'guest';
    }

    const profile = await response.json();

    // Возвращаем роль пользователя из профиля
    const role = profile.role as UserRole;

    // Валидация роли - если роль неизвестна, используем retail как fallback
    const validRoles: UserRole[] = [
      'retail',
      'wholesale_level1',
      'wholesale_level2',
      'wholesale_level3',
      'trainer',
      'federation_rep',
      'admin',
      'guest',
    ];

    return validRoles.includes(role) ? role : 'retail';
  } catch (error) {
    console.error('Error getting user role:', error);
    return 'guest';
  }
}

/**
 * Генерирует метаданные для SEO
 */
export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  try {
    const product = await productsService.getProductBySlug(params.slug);

    const primaryImage = product.images.find(img => img.is_primary) || product.images[0];

    return {
      title: `${product.name} - ${product.brand} | FREESPORT`,
      description: product.description.substring(0, 160),
      openGraph: {
        title: product.name,
        description: product.description,
        images: primaryImage
          ? [{ url: primaryImage.image, alt: primaryImage.alt_text || product.name }]
          : [],
        type: 'website',
      },
      alternates: {
        canonical: `/product/${product.slug}`,
      },
    };
  } catch {
    return {
      title: 'Товар не найден | FREESPORT',
      description: 'Запрошенный товар не найден',
    };
  }
}

/**
 * Product Detail Page Component
 */
export default async function ProductPage({ params }: ProductPageProps) {
  let product;
  let userRole: UserRole = 'guest';

  try {
    // Загружаем данные товара и роль пользователя параллельно
    [product, userRole] = await Promise.all([
      productsService.getProductBySlug(params.slug),
      getUserRole(),
    ]);
  } catch (error) {
    console.error('Error loading product:', error);
    notFound();
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Breadcrumbs */}
      <ProductBreadcrumbs breadcrumbs={product.category.breadcrumbs} productName={product.name} />

      {/* Main Content - Client Component для интеграции с вариантами */}
      <ProductPageClient product={product} userRole={userRole} />
    </div>
  );
}
