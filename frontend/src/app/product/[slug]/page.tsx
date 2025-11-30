/**
 * Product Detail Page (Story 12.1)
 * SSR страница детального просмотра товара
 */

import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { cookies } from 'next/headers';
import productsService from '@/services/productsService';
import ProductBreadcrumbs from '@/components/product/ProductBreadcrumbs';
import ProductInfo from '@/components/product/ProductInfo';
import ProductSpecs from '@/components/product/ProductSpecs';
import ProductImageGallery from '@/components/product/ProductImageGallery';
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

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
        {/* Left Column: Image Gallery (2/3) */}
        <div className="lg:col-span-2">
          {/* Product Images with Zoom/Lightbox */}
          <ProductImageGallery images={product.images} productName={product.name} />

          {/* Product Specifications */}
          <div className="mt-8">
            <ProductSpecs specifications={product.specifications} />
          </div>
        </div>

        {/* Right Column: Product Summary (1/3) - Sticky */}
        <div className="lg:col-span-1">
          <div className="lg:sticky lg:top-24">
            <div className="bg-white rounded-lg border border-neutral-200 p-6">
              <ProductInfo product={product} userRole={userRole} />

              {/* Add to Cart Button */}
              {(product.is_in_stock || product.can_be_ordered) && (
                <button className="w-full mt-6 px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                  Добавить в корзину
                </button>
              )}
            </div>

            {/* Schema.org Product Structured Data */}
            <script
              type="application/ld+json"
              dangerouslySetInnerHTML={{
                __html: JSON.stringify({
                  '@context': 'https://schema.org',
                  '@type': 'Product',
                  name: product.name,
                  image: product.images.map(img => img.image),
                  description: product.description,
                  sku: product.sku,
                  brand: {
                    '@type': 'Brand',
                    name: product.brand,
                  },
                  offers: {
                    '@type': 'Offer',
                    url: `https://freesport.ru/product/${product.slug}`,
                    priceCurrency: product.price.currency,
                    price: product.price.retail,
                    availability: product.is_in_stock
                      ? 'https://schema.org/InStock'
                      : product.can_be_ordered
                        ? 'https://schema.org/PreOrder'
                        : 'https://schema.org/OutOfStock',
                  },
                  aggregateRating: product.rating
                    ? {
                        '@type': 'AggregateRating',
                        ratingValue: product.rating,
                        reviewCount: product.reviews_count || 0,
                      }
                    : undefined,
                }),
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
