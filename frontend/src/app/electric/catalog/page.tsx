/**
 * Страница каталога товаров FREESPORT Platform (Electric Orange Edition)
 * Parallel Route for Design System Migration
 */

'use client';

import React, { useCallback, useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

// Electric Orange Components
import ElectricProductCard from '@/components/ui/ProductCard/ElectricProductCard';
import ElectricSidebar from '@/components/ui/Sidebar/ElectricSidebar';
import ElectricSectionHeader from '@/components/ui/SectionHeader/ElectricSectionHeader';
import ElectricPagination from '@/components/ui/Pagination/ElectricPagination';
import ElectricSpinner from '@/components/ui/Spinner/ElectricSpinner';
import { useToast } from '@/components/ui/Toast';

// Services & Type Definitions
import productsService, { type ProductFilters } from '@/services/productsService';
import categoriesService from '@/services/categoriesService';
import brandsService from '@/services/brandsService';
import type { Product, CategoryTree as CategoryTreeResponse, Brand } from '@/types/api';
import { useCartStore } from '@/stores/cartStore';

// Icons & Utils
import { ArrowLeft } from 'lucide-react';

// ============================================
// Types reuse
// ============================================

type PriceRange = {
  min: number;
  max: number;
};

type CategoryNode = {
  id: number;
  label: string;
  slug?: string;
  count?: number; // Added for ElectricSidebar compatibility
  children?: CategoryNode[];
};

// ============================================
// Constants
// ============================================

const PRICE_MIN = 1;
const PRICE_MAX = 50000;
const DEFAULT_PRICE_RANGE: PriceRange = { min: PRICE_MIN, max: PRICE_MAX };
const PAGE_SIZE = 12;
const DEFAULT_ORDERING = '-created_at';
const DEFAULT_CATEGORY_LABEL = 'Спорт';

const mapCategoryTreeNode = (node: CategoryTreeResponse): CategoryNode => ({
  id: node.id,
  label: node.name,
  slug: node.slug,
  children: node.children?.map(mapCategoryTreeNode),
});

const findCategoryBySlug = (nodes: CategoryNode[], targetSlug: string): CategoryNode | null => {
  for (const node of nodes) {
    if (node.slug === targetSlug) return node;
    if (node.children) {
      const child = findCategoryBySlug(node.children, targetSlug);
      if (child) return child;
    }
  }
  return null;
};

const findCategoryByLabel = (nodes: CategoryNode[], targetLabel: string): CategoryNode | null => {
  for (const node of nodes) {
    if (node.label === targetLabel) return node;
    if (node.children) {
      const child = findCategoryByLabel(node.children, targetLabel);
      if (child) return child;
    }
  }
  return null;
};

// ============================================
// Main Component
// ============================================

const ElectricCatalogPage: React.FC = () => {
  const searchParams = useSearchParams();

  // State
  const [activeCategoryId, setActiveCategoryId] = useState<number | null>(null);
  const [activeCategoryLabel, setActiveCategoryLabel] = useState(DEFAULT_CATEGORY_LABEL);

  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrandIds, setSelectedBrandIds] = useState<Set<number>>(new Set());

  const [priceRange, setPriceRange] = useState<PriceRange>(DEFAULT_PRICE_RANGE);
  const [searchQuery, setSearchQuery] = useState('');

  const [products, setProducts] = useState<Product[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [page, setPage] = useState(1);
  const [ordering] = useState(DEFAULT_ORDERING);

  const [isProductsLoading, setIsProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);

  // Cart
  const { addItem } = useCartStore();
  const { success, error: toastError } = useToast();

  // --------------------------------------------
  // Data Fetching: Categories & Brands
  // --------------------------------------------

  useEffect(() => {
    let isMounted = true;

    const fetchCategories = async () => {
      try {
        const tree = await categoriesService.getTree();
        if (!isMounted) return;
        const mapped = tree.map(mapCategoryTreeNode);

        const categorySlug = searchParams.get('category');
        let initialCategory: CategoryNode | null = null;

        if (categorySlug) {
          initialCategory = findCategoryBySlug(mapped, categorySlug);
        }
        if (!initialCategory) {
          initialCategory =
            findCategoryByLabel(mapped, DEFAULT_CATEGORY_LABEL) ?? mapped[0] ?? null;
        }

        if (initialCategory) {
          setActiveCategoryId(initialCategory.id);
          setActiveCategoryLabel(initialCategory.label);
        }
      } catch (error) {
        console.error('Failed to load categories', error);
      }
    };

    fetchCategories();
    return () => {
      isMounted = false;
    };
  }, [searchParams]);

  useEffect(() => {
    let isMounted = true;
    const fetchBrands = async () => {
      try {
        const data = await brandsService.getAll();
        if (isMounted) setBrands(data);
      } catch (error) {
        console.error('Failed to load brands', error);
      }
    };
    fetchBrands();
    return () => {
      isMounted = false;
    };
  }, []);

  // --------------------------------------------
  // URL & Filters Sync
  // --------------------------------------------

  useEffect(() => {
    const searchFromUrl = searchParams.get('search');
    if (searchFromUrl) setSearchQuery(searchFromUrl);
  }, [searchParams]);

  // --------------------------------------------
  // Products Fetching
  // --------------------------------------------

  const fetchProducts = useCallback(async () => {
    try {
      setIsProductsLoading(true);
      setProductsError(null);

      const filters: ProductFilters = {
        page,
        page_size: PAGE_SIZE,
        ordering,
        min_price: priceRange.min,
        max_price: priceRange.max,
        in_stock: true,
      };

      if (activeCategoryId) filters.category_id = activeCategoryId;
      if (selectedBrandIds.size > 0) filters.brand = Array.from(selectedBrandIds).join(',');
      if (searchQuery.trim().length >= 2) filters.search = searchQuery.trim();

      const response = await productsService.getAll(filters);
      setProducts(response.results);
      setTotalProducts(response.count);
    } catch (error) {
      console.error('Failed to load products', error);
      setProductsError('Не удалось загрузить товары');
    } finally {
      setIsProductsLoading(false);
    }
  }, [activeCategoryId, ordering, page, priceRange, selectedBrandIds, searchQuery]);

  useEffect(() => {
    if (activeCategoryId !== null) {
      fetchProducts();
    }
  }, [fetchProducts, activeCategoryId]);

  // --------------------------------------------
  // Handlers
  // --------------------------------------------

  const handleFilterChange = (groupId: string, optionId: string, checked: boolean) => {
    // Categories
    if (groupId === 'categories') {
      // Since ElectricSidebar handles categories as checkboxes/toggles, we need to map back to IDs
      // This part might need adjustment depending on how ElectricSidebar exposes IDs
      // For now, let's assume optionId is the string ID of the category
      // but our categories use numeric IDs.
      // The sidebar is generic. Let's try to map string id back to numeric if possible.
      // Optimization: ElectricSidebar generally expects string IDs.
      // We can reimplement handleSelectCategory logic here if needed,
      // but treating categories as a single-select filter in the sidebar is cleaner visually.
    }

    // Brands
    if (groupId === 'brands') {
      const brandId = Number(optionId);
      if (!isNaN(brandId)) {
        setSelectedBrandIds(prev => {
          const next = new Set(prev);
          if (checked) next.add(brandId);
          else next.delete(brandId);
          return next;
        });
        setPage(1);
      }
    }
  };

  const handlePriceChange = (range: { min: number; max: number }) => {
    setPriceRange(range);
    setPage(1);
  };

  const handleAddToCart = useCallback(
    async (productId: number) => {
      // Reuse existing logic from original page
      const product = products.find(p => p.id === productId);
      if (!product) return;

      try {
        const productDetail = await productsService.getProductBySlug(product.slug);
        const availableVariant = productDetail.variants?.find(v => v.is_in_stock);

        if (!availableVariant) {
          toastError('Товар недоступен');
          return;
        }

        const result = await addItem(availableVariant.id, 1);
        if (result.success) success(`${product.name} добавлен`);
        else toastError(result.error || 'Ошибка');
      } catch {
        toastError('Ошибка добавления');
      }
    },
    [products, addItem, success, toastError]
  );

  // --------------------------------------------
  // Adapters for Sidebar
  // --------------------------------------------

  // Transform Category Tree for Sidebar
  // We flatten the tree or just show top levels for the filter?
  // Let's emulate the visual style: Categories as a checklist or radio.
  // Original catalog uses a tree. ElectricSidebar uses `filterGroups`.

  // Let's create a custom adapter to convert the tree active path into sidebar options if needed.
  // Or, simply pass the relevant categories.

  const brandFilterOptions = brands.map(brand => ({
    id: String(brand.id),
    label: brand.name,
  }));

  // --------------------------------------------
  // Render
  // --------------------------------------------

  const totalPages = Math.max(1, Math.ceil(totalProducts / PAGE_SIZE));

  return (
    <div className="min-h-screen bg-[var(--bg-body)] text-[var(--color-text-primary)] font-body selection:bg-[var(--color-primary)] selection:text-[var(--color-text-inverse)]">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6">
          <div className="space-y-2">
            <Link
              href="/"
              className="inline-flex items-center text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors mb-2"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Вернуться на главную
            </Link>
            <ElectricSectionHeader title={activeCategoryLabel} size="lg" />
            <p className="text-[var(--color-text-secondary)]">Найдено {totalProducts} товаров</p>
          </div>

          <div className="flex gap-4">{/* Ordering Select could go here */}</div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <aside className="w-full lg:w-[240px] flex-shrink-0">
            <ElectricSidebar
              filterGroups={[
                {
                  id: 'brands',
                  title: 'БРЕНДЫ',
                  type: 'checkbox',
                  options: brandFilterOptions,
                },
                {
                  id: 'price',
                  title: 'ЦЕНА (₽)',
                  type: 'price',
                  options: [],
                },
              ]}
              priceRange={{ min: PRICE_MIN, max: PRICE_MAX }}
              currentPrice={priceRange}
              selectedFilters={{
                brands: Array.from(selectedBrandIds).map(String),
              }}
              onFilterChange={handleFilterChange}
              onPriceChange={handlePriceChange}
              className="w-full"
            />
            {/* 
              Note: Category navigation in sidebar in original design is a Tree. 
              ElectricSidebar uses generic checklists. 
              Ideally we should enhance ElectricSidebar to support Trees or 
              render the CategoryTree component styled for Electric Orange separately.
              For this iteration, we keep brands and price and category is selected via URL/Header or we add a simple list.
            */}
          </aside>

          {/* Product Grid */}
          <main className="flex-1 min-w-0">
            {isProductsLoading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    className="aspect-square bg-[var(--bg-card)] flex items-center justify-center transform -skew-x-12 border border-[var(--border-default)]"
                  >
                    <ElectricSpinner size="md" />
                  </div>
                ))}
              </div>
            ) : productsError ? (
              <div className="p-8 text-center border border-[var(--color-danger)] bg-[var(--color-danger-bg)] text-[var(--color-danger)]">
                {productsError}
              </div>
            ) : products.length === 0 ? (
              <div className="p-12 text-center text-[var(--color-text-secondary)]">
                Товары не найдены
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
                {products.map(product => {
                  // Badge logic
                  let badge: 'primary' | 'sale' | 'hit' | 'new' | undefined;
                  if (product.is_sale) badge = 'sale';
                  else if (product.is_hit) badge = 'hit';
                  else if (product.is_new) badge = 'new';

                  // Image logic
                  const imageUrl =
                    product.main_image ||
                    product.image ||
                    product.images?.[0]?.image ||
                    '/placeholder.png';

                  return (
                    <ElectricProductCard
                      key={product.id}
                      image={imageUrl}
                      title={product.name}
                      brand={product.brand?.name}
                      price={product.retail_price}
                      // Calculate old price if discount exists, or just pass undefined if not available in API
                      oldPrice={
                        product.is_sale && product.discount_percent
                          ? Math.round(product.retail_price / (1 - product.discount_percent / 100))
                          : undefined
                      }
                      badge={badge}
                      inStock={product.is_in_stock}
                      onAddToCart={() => handleAddToCart(product.id)}
                      isFavorite={false}
                      onToggleFavorite={() => {}}
                    />
                  );
                })}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-16">
                <ElectricPagination
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={setPage}
                />
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[var(--bg-body)] flex items-center justify-center text-[var(--color-primary)]">
          Loading...
        </div>
      }
    >
      <ElectricCatalogPage />
    </Suspense>
  );
}
