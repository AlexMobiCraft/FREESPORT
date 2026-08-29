/**
 * Unit-тесты для интеграции поиска в CatalogPage (Story 18.4)
 */

import { describe, it, expect, vi, beforeEach, afterAll, type Mock } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CatalogPage from '../page';

// Mock данные для тестов
const mockProducts = [
  {
    id: 1,
    name: 'Nike Air Max 90',
    slug: 'nike-air-max-90',
    retail_price: 12990,
    main_image: '/images/nike-air-max.jpg',
    is_in_stock: true,
    stock_quantity: 10,
    can_be_ordered: true,
    brand: { id: 1, name: 'Nike', slug: 'nike', is_featured: false },
    category: { id: 1, name: 'Обувь', slug: 'shoes' },
    is_hit: false,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
  {
    id: 2,
    name: 'Nike Dunk Low',
    slug: 'nike-dunk-low',
    retail_price: 9990,
    main_image: '/images/nike-dunk.jpg',
    is_in_stock: true,
    stock_quantity: 5,
    can_be_ordered: true,
    brand: { id: 1, name: 'Nike', slug: 'nike', is_featured: false },
    category: { id: 1, name: 'Обувь', slug: 'shoes' },
    is_hit: false,
    is_new: false,
    is_sale: false,
    is_promo: false,
    is_premium: false,
    discount_percent: null,
  },
];

const mockApiResponse = {
  count: 2,
  next: null,
  previous: null,
  results: mockProducts,
};

const mockCategories = [
  {
    id: 1,
    name: 'Спорт',
    slug: 'sport',
    children: [],
  },
];

const mockBrands = [
  { id: 1, name: 'Nike', slug: 'nike' },
  { id: 2, name: 'Adidas', slug: 'adidas' },
];

// Mock для productsService
vi.mock('@/services/productsService', () => ({
  default: {
    getAll: vi.fn(() => Promise.resolve(mockApiResponse)),
    search: vi.fn(() => Promise.resolve({ results: mockProducts })),
    getProductBySlug: vi.fn(() =>
      Promise.resolve({
        ...mockProducts[0],
        variants: [
          {
            id: 1,
            sku: 'NIKE-001',
            is_in_stock: true,
            stock_quantity: 10,
            current_price: '12990',
          },
        ],
      })
    ),
  },
}));

// Mock для categoriesService
vi.mock('@/services/categoriesService', () => ({
  default: {
    getTree: vi.fn(() => Promise.resolve(mockCategories)),
    getVisibleCategories: vi.fn(() => Promise.resolve([1])),
  },
}));

// Mock для brandsService
vi.mock('@/services/brandsService', () => ({
  default: {
    getAll: vi.fn(() => Promise.resolve(mockBrands)),
    getVisibleBrands: vi.fn(() => Promise.resolve([1, 2])),
  },
}));

// Mock для cartStore
vi.mock('@/stores/cartStore', () => ({
  useCartStore: vi.fn(() => ({
    addItem: vi.fn(() => Promise.resolve({ success: true })),
  })),
}));

// Mock для Toast
vi.mock('@/components/ui/Toast', () => ({
  useToast: vi.fn(() => ({
    success: vi.fn(),
    error: vi.fn(),
  })),
}));

// Mock для next/navigation.
let mockSearchParams = new URLSearchParams();

/** Хронологический журнал навигаций: push и replace в одном порядке вызова */
type Navigation = { type: 'push' | 'replace'; url: string };
const navigationLog: Navigation[] = [];

const applyNavigation = (type: Navigation['type']) => (url: string) => {
  const queryIndex = url.indexOf('?');
  mockSearchParams = new URLSearchParams(queryIndex === -1 ? '' : url.slice(queryIndex + 1));
  navigationLog.push({ type, url });
};

const resetSearchParams = (query = '') => {
  mockSearchParams = new URLSearchParams(query);
  navigationLog.length = 0;
};

// По умолчанию роутер-мок — пустышка: навигация без последствий, как было
// до появления пагинации в URL. Блоки, которым нужна честная навигация,
// включают её через enableRouterNavigation() и возвращают исходные
// реализации через restoreRouterMocks() в afterAll.
const mockPush = vi.fn();
const mockReplace = vi.fn();

const enableRouterNavigation = () => {
  mockPush.mockImplementation(applyNavigation('push'));
  mockReplace.mockImplementation(applyNavigation('replace'));
};

const restoreRouterMocks = () => {
  mockPush.mockReset();
  mockReplace.mockReset();
};

vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: mockPush,
    replace: mockReplace,
  })),
  useSearchParams: vi.fn(() => mockSearchParams),
  usePathname: vi.fn(() => '/catalog'),
}));

describe('CatalogPage - Search Integration (Story 18.4)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    resetSearchParams();
    mockPush.mockClear();

    // Mock matchMedia for responsive filter state
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: query === '(min-width: 1024px)', // Simulate desktop
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it('AC 1: должен отображать SearchField на странице каталога', async () => {
    render(<CatalogPage />);

    await waitFor(() => {
      const searchField = screen.getByPlaceholderText('Поиск в каталоге...');
      expect(searchField).toBeInTheDocument();
    });
  });

  it('AC 3: должен обновлять URL с параметром search при вводе запроса', async () => {
    const user = userEvent.setup();
    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Вводим поисковый запрос
    await user.type(searchInput, 'nike');

    // Ждем debounce (300ms)
    await waitFor(
      () => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining('search=nike'),
          expect.anything()
        );
      },
      { timeout: 500 }
    );
  });

  it('AC 2, AC 4: должен передавать параметр search в API вместе с существующими фильтрами', async () => {
    const user = userEvent.setup();
    const productsService = await import('@/services/productsService');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Вводим поисковый запрос
    await user.type(searchInput, 'nike');

    // Ждем debounce и вызов API
    await waitFor(
      () => {
        expect(productsService.default.getAll).toHaveBeenCalledWith(
          expect.objectContaining({
            search: 'nike',
          })
        );
      },
      { timeout: 500 }
    );
  });

  it('AC 3: должен удалять параметр search из URL при пустом запросе', async () => {
    const user = userEvent.setup();

    // Запрос уже в URL: SearchAutocomplete держит текст поля во внутреннем
    // состоянии, поэтому вводим его и в поле — только так очистка меняет URL
    resetSearchParams('search=test');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Вводим поисковый запрос
    await user.type(searchInput, 'test');

    // Ждем появления кнопки очистки
    await waitFor(() => {
      expect(screen.getByLabelText('Очистить поиск')).toBeInTheDocument();
    });

    // Очищаем поле через кнопку очистки
    const clearButton = screen.getByLabelText('Очистить поиск');
    await user.click(clearButton);

    // Проверяем, что URL обновлен без параметра search
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/catalog', expect.anything());
    });
  });

  it('AC 5: должен сбрасывать поисковый запрос при нажатии кнопки "Сбросить"', async () => {
    const user = userEvent.setup();

    // Запрос уже в URL — иначе сбрасывать в адресной строке нечего
    resetSearchParams('search=nike');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Вводим поисковый запрос
    await user.type(searchInput, 'nike');

    await waitFor(() => {
      expect(searchInput).toHaveValue('nike');
    });

    // Нажимаем кнопку "Сбросить"
    const resetButton = screen.getByText('Сбросить');
    await user.click(resetButton);

    // Проверяем, что поисковый запрос сброшен
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/catalog', expect.anything());
    });
  });

  it('AC 2: должен показывать индикатор результатов при активном поиске', async () => {
    const user = userEvent.setup();
    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Вводим поисковый запрос
    await user.type(searchInput, 'nike');

    // Проверяем, что индикатор результатов отображается
    await waitFor(
      () => {
        const indicator = screen.getByText(/Найдено.*товар.*по запросу «nike»/i);
        expect(indicator).toBeInTheDocument();
        expect(indicator).toHaveAttribute('aria-live', 'polite');
        expect(indicator).toHaveAttribute('role', 'status');
      },
      { timeout: 500 }
    );
  });

  it('должен читать параметр search из URL при загрузке страницы', async () => {
    // Устанавливаем параметр search в URL
    resetSearchParams('search=adidas');

    const productsService = await import('@/services/productsService');

    render(<CatalogPage />);

    // Проверяем, что API вызван с параметром search из URL
    await waitFor(() => {
      expect(productsService.default.getAll).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'adidas',
        })
      );
    });
  });

  it('не должен отправлять параметр search если длина меньше minLength (2 символа)', async () => {
    const user = userEvent.setup();
    const productsService = await import('@/services/productsService');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Поиск в каталоге...')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Поиск в каталоге...');

    // Очищаем предыдущие вызовы
    vi.clearAllMocks();

    // Вводим 1 символ
    await user.type(searchInput, 'n');

    // Ждем debounce, обернув в act чтобы поймать обновление состояния
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 400));
    });

    // Проверяем, что API не был вызван с параметром search
    const calls = (productsService.default.getAll as Mock).mock.calls;
    const callsWithSearch = calls.filter((call: Array<Record<string, unknown>>) => call[0]?.search);
    expect(callsWithSearch).toHaveLength(0);
  });

  it('AC 4: должен отображать состояния загрузки (Skeleton) при ожидании категорий', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    const categoriesService = await import('@/services/categoriesService');
    // Мокаем API с задержкой
    (categoriesService.default.getTree as Mock).mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve(mockCategories), 100))
    );

    render(<CatalogPage />);

    // Проверяем наличие Skeleton
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading.querySelector('.animate-pulse')).toBeInTheDocument();

    // Разрешаем таймер
    act(() => {
      vi.runAllTimers();
    });

    // Ждем разрешения категории
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Каталог' })).toBeInTheDocument();
    });

    vi.useRealTimers();
  });

  it('AC 3: должен содержать корректную семантику: <search role="search"> и правильный порядок DOM для H1', async () => {
    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByRole('search')).toBeInTheDocument();
    });

    const searchRegion = screen.getByRole('search');
    expect(searchRegion.tagName.toLowerCase()).toBe('search');

    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveClass('text-neutral-900');

    const parent = heading.parentElement;
    if (parent) {
      const children = Array.from(parent.children);
      const headingIndex = children.indexOf(heading);
      const searchIndex = children.indexOf(searchRegion);
      expect(headingIndex).toBeLessThan(searchIndex);
    }
  });

  it('F4: фильтры должны быть свёрнуты на мобильных устройствах', async () => {
    // Переопределяем matchMedia для мобильного устройства
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: false, // Мобильное устройство — ни один media query не совпадает
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });

    render(<CatalogPage />);

    await waitFor(() => {
      // Проверяем, что кнопки фильтров имеют aria-expanded="false"
      const categoryButton = screen.getByRole('button', { name: /Категории/i });
      expect(categoryButton).toHaveAttribute('aria-expanded', 'false');

      const brandButton = screen.getByRole('button', { name: /Бренд/i });
      expect(brandButton).toHaveAttribute('aria-expanded', 'false');
    });
  });
});

// ---------------------------------------------------------------------------
// Тесты сортировки и скрытия пустых категорий (bugfix: Без категории)
// ---------------------------------------------------------------------------
import categoriesService from '@/services/categoriesService';
import brandsService from '@/services/brandsService';

const mockMatchMedia = () => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(min-width: 1024px)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
};

describe('CatalogPage — сортировка и скрытие пустых категорий', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMatchMedia();
    resetSearchParams();
    // Сбрасываем getVisibleCategories к дефолтному значению
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([1]);
  });

  it('не показывает категорию Без категории если она скрыта (in_stock_count=0)', async () => {
    (categoriesService.getTree as Mock).mockResolvedValue([
      { id: 1, name: 'Обувь', slug: 'shoes', in_stock_count: 5, products_count: 5, children: [] },
      {
        id: 2,
        name: 'Без категории',
        slug: 'uncategorized',
        in_stock_count: 0,
        products_count: 3,
        children: [],
      },
    ]);
    // visible-categories не возвращает uncategorized (нет in_stock товаров)
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([1]);

    render(<CatalogPage />);

    // Открываем панель категорий
    const categoryBtn = await screen.findByRole('button', { name: /Категории/i });
    await act(async () => {
      categoryBtn.click();
    });

    await waitFor(() => {
      expect(screen.queryByText('Без категории')).not.toBeInTheDocument();
      expect(screen.getByText('Обувь')).toBeInTheDocument();
    });
  });

  it('показывает "Нет категорий" если все категории скрыты', async () => {
    (categoriesService.getTree as Mock).mockResolvedValue([
      { id: 1, name: 'Обувь', slug: 'shoes', in_stock_count: 3, products_count: 3, children: [] },
    ]);
    // visible-categories вернул пустой список
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([]);

    render(<CatalogPage />);

    const categoryBtn = await screen.findByRole('button', { name: /Категории/i });
    await act(async () => {
      categoryBtn.click();
    });

    await waitFor(() => {
      expect(screen.getByText('Нет категорий')).toBeInTheDocument();
    });
  });

  it('показывает весь список если getVisibleCategories вернул ошибку (graceful degradation)', async () => {
    (categoriesService.getTree as Mock).mockResolvedValue([
      { id: 1, name: 'Обувь', slug: 'shoes', in_stock_count: 3, products_count: 3, children: [] },
      {
        id: 2,
        name: 'Без категории',
        slug: 'uncategorized',
        in_stock_count: 0,
        products_count: 1,
        children: [],
      },
    ]);
    (categoriesService.getVisibleCategories as Mock).mockRejectedValue(new Error('500'));

    render(<CatalogPage />);

    const categoryBtn = await screen.findByRole('button', { name: /Категории/i });
    await act(async () => {
      categoryBtn.click();
    });

    await waitFor(() => {
      // При ошибке fallback = показывать всё дерево
      expect(screen.getByText('Обувь')).toBeInTheDocument();
      expect(screen.getByText('Без категории')).toBeInTheDocument();
    });
  });

  it('сохраняет родительскую категорию видимой если дочерняя видима', async () => {
    (categoriesService.getTree as Mock).mockResolvedValue([
      {
        id: 10,
        name: 'Спорт',
        slug: 'sport',
        in_stock_count: 0,
        products_count: 0,
        children: [
          {
            id: 11,
            name: 'Лыжи',
            slug: 'skiing',
            in_stock_count: 2,
            products_count: 2,
            children: [],
          },
        ],
      },
    ]);
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([11]); // только дочерняя

    render(<CatalogPage />);

    const categoryBtn = await screen.findByRole('button', { name: /Категории/i });
    await act(async () => {
      categoryBtn.click();
    });

    await waitFor(() => {
      // Родитель виден потому что дочерняя видима
      expect(screen.getByText('Спорт')).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Тесты скрытия брендов без товаров и динамического visible-brands
// ---------------------------------------------------------------------------

describe('CatalogPage — видимость брендов по наличию и фильтрам', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMatchMedia();
    resetSearchParams();
    (categoriesService.getTree as Mock).mockResolvedValue([
      { id: 1, name: 'Футбол', slug: 'football', in_stock_count: 5, products_count: 5, children: [] },
    ]);
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([1]);
    (brandsService.getAll as Mock).mockResolvedValue(mockBrands);
    (brandsService.getVisibleBrands as Mock).mockResolvedValue([1, 2]);
  });

  it('вызывает первичную загрузку брендов с has_stock=true', async () => {
    render(<CatalogPage />);

    await waitFor(() => {
      expect(brandsService.getAll).toHaveBeenCalledWith({ has_stock: true });
    });
  });

  it('не показывает out-of-stock бренд, если его нет в первичном ответе getAll', async () => {
    (brandsService.getAll as Mock).mockResolvedValue([{ id: 2, name: 'Adidas', slug: 'adidas' }]);

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByLabelText('Adidas')).toBeInTheDocument();
      expect(screen.queryByLabelText('Nike')).not.toBeInTheDocument();
    });
  });

  it('скрывает бренды, которых нет в visible-brands', async () => {
    (brandsService.getVisibleBrands as Mock).mockResolvedValue([1]);

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByLabelText('Nike')).toBeInTheDocument();
      expect(screen.queryByLabelText('Adidas')).not.toBeInTheDocument();
    });
  });

  it('сохраняет выбранный бренд видимым, даже если он не входит в visible-brands', async () => {
    const user = userEvent.setup();
    (brandsService.getVisibleBrands as Mock)
      .mockResolvedValueOnce([1, 2])
      .mockResolvedValueOnce([]);

    render(<CatalogPage />);

    const nike = await screen.findByLabelText('Nike');
    await user.click(nike);

    await waitFor(() => {
      expect(screen.getByLabelText('Nike')).toBeInTheDocument();
      expect(screen.queryByLabelText('Adidas')).not.toBeInTheDocument();
    });
  });

  it('показывает полный список брендов при сетевой ошибке visible-brands', async () => {
    (brandsService.getVisibleBrands as Mock).mockRejectedValue(new Error('500'));

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByLabelText('Nike')).toBeInTheDocument();
      expect(screen.getByLabelText('Adidas')).toBeInTheDocument();
    });
  });

  it('показывает "Бренды не найдены", когда visible-brands пустой и нет выбора', async () => {
    (brandsService.getVisibleBrands as Mock).mockResolvedValue([]);

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByText('Бренды не найдены')).toBeInTheDocument();
      expect(screen.queryByLabelText('Nike')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Adidas')).not.toBeInTheDocument();
    });
  });

  it('сбрасывает sidebarVisibleBrandIds при снятии чекбокса "В наличии"', async () => {
    const user = userEvent.setup();
    (brandsService.getVisibleBrands as Mock).mockResolvedValue([]);

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByText('Бренды не найдены')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('В наличии'));

    await waitFor(() => {
      expect(screen.getByLabelText('Nike')).toBeInTheDocument();
      expect(screen.getByLabelText('Adidas')).toBeInTheDocument();
    });
  });
});


// ---------------------------------------------------------------------------
// Тесты сохранения номера страницы в URL
// (bugfix: пагинация сбрасывалась на первую страницу при обновлении браузера)
// ---------------------------------------------------------------------------
import productsService from '@/services/productsService';

/** 40 товаров при PAGE_SIZE=12 → 4 страницы пагинации */
const buildProductsResponse = (count: number) => ({
  count,
  next: null,
  previous: null,
  results: mockProducts,
});

/** Последняя навигация по хронологии — не по склейке двух массивов вызовов */
const lastNavigation = (): Navigation | null => navigationLog.at(-1) ?? null;

/** Последний URL, переданный в push/replace */
const lastNavigationUrl = () => lastNavigation()?.url ?? null;

describe('CatalogPage — сохранение страницы пагинации в URL', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMatchMedia();
    // Честный роутер-мок: push/replace меняют то, что вернёт следующий
    // useSearchParams(). Пустышка делала бы навигацию беспоследственной,
    // и регрессии «клик по странице перезапускает эффекты на [searchParams]»
    // были бы не видны в тестах.
    enableRouterNavigation();
    resetSearchParams();
    (productsService.getAll as Mock).mockResolvedValue(buildProductsResponse(40));
    (categoriesService.getTree as Mock).mockResolvedValue(mockCategories);
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([1]);
    (brandsService.getAll as Mock).mockResolvedValue(mockBrands);
    (brandsService.getVisibleBrands as Mock).mockResolvedValue([1, 2]);
  });

  afterAll(() => {
    // Возвращаем исходные (пустышечные) реализации, чтобы честная навигация
    // не протекала в блоки, написанные под беспоследственный push
    restoreRouterMocks();
    resetSearchParams();
  });

  it('читает номер страницы из URL при монтировании (сценарий F5)', async () => {
    resetSearchParams('page=3');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 3 }));
    });
  });

  it('пишет page в URL при клике по номеру страницы', async () => {
    const user = userEvent.setup();

    render(<CatalogPage />);

    await user.click(await screen.findByRole('button', { name: '3' }));

    expect(lastNavigationUrl()).toBe('/catalog?page=3');
    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 3 }));
    });
  });

  it('делает ровно один запрос товаров на клик по странице', async () => {
    const user = userEvent.setup();

    render(<CatalogPage />);

    await screen.findByRole('button', { name: '3' });
    (productsService.getAll as Mock).mockClear();
    (categoriesService.getTree as Mock).mockClear();

    await user.click(screen.getByRole('button', { name: '3' }));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 3 }));
    });
    // Смена URL не должна перезапускать эффекты, завязанные на searchParams
    expect(productsService.getAll).toHaveBeenCalledTimes(1);
    expect(categoriesService.getTree).not.toHaveBeenCalled();
  });

  it('убирает page из URL при возврате на первую страницу', async () => {
    const user = userEvent.setup();
    resetSearchParams('page=3');

    render(<CatalogPage />);

    await user.click(await screen.findByRole('button', { name: '1' }));

    expect(lastNavigationUrl()).toBe('/catalog');
  });

  it('помечает активную страницу через aria-current', async () => {
    resetSearchParams('page=2');

    render(<CatalogPage />);

    const active = await screen.findByRole('button', { name: '2' });
    expect(active).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: '3' })).not.toHaveAttribute('aria-current');
  });

  it('сохраняет остальные параметры URL при смене страницы', async () => {
    const user = userEvent.setup();
    resetSearchParams('search=nike&page=2');

    render(<CatalogPage />);

    await user.click(await screen.findByRole('button', { name: '3' }));

    const url = lastNavigationUrl() ?? '';
    expect(url).toContain('search=nike');
    expect(url).toContain('page=3');
  });

  it('сбрасывает страницу одним запросом при смене фильтра', async () => {
    const user = userEvent.setup();
    resetSearchParams('page=3');

    render(<CatalogPage />);

    await screen.findByLabelText('Nike');
    (productsService.getAll as Mock).mockClear();
    mockPush.mockClear();

    await user.click(screen.getByLabelText('Nike'));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
    });
    // Ровно один запрос: старая страница вместе с новым фильтром не запрашивается
    expect(productsService.getAll).toHaveBeenCalledTimes(1);
    expect(lastNavigationUrl()).toBe('/catalog');
  });

  it('не откатывает выбранную в сайдбаре категорию при клике по странице', async () => {
    const user = userEvent.setup();
    resetSearchParams('category=sport');
    (categoriesService.getTree as Mock).mockResolvedValue([
      { id: 1, name: 'Спорт', slug: 'sport', in_stock_count: 5, products_count: 5, children: [] },
      { id: 2, name: 'Обувь', slug: 'shoes', in_stock_count: 5, products_count: 5, children: [] },
    ]);
    (categoriesService.getVisibleCategories as Mock).mockResolvedValue([1, 2]);

    render(<CatalogPage />);

    await user.click(await screen.findByText('Обувь'));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({ category_id: 2 })
      );
    });

    (productsService.getAll as Mock).mockClear();
    await user.click(await screen.findByRole('button', { name: '2' }));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }));
    });
    // Категория из URL (sport) не должна вытеснить выбранную в сайдбаре (shoes)
    expect(productsService.getAll).toHaveBeenLastCalledWith(
      expect.objectContaining({ category_id: 2, page: 2 })
    );
  });

  it('не схлопывает мультивыбор брендов при клике по странице', async () => {
    const user = userEvent.setup();
    resetSearchParams('brand=nike');

    render(<CatalogPage />);

    await user.click(await screen.findByLabelText('Adidas'));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(
        expect.objectContaining({ brand: '1,2' })
      );
    });

    (productsService.getAll as Mock).mockClear();
    await user.click(await screen.findByRole('button', { name: '2' }));

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenLastCalledWith(
        expect.objectContaining({ brand: '1,2', page: 2 })
      );
    });
  });

  it.each(['page=abc', 'page=0', 'page=-1', 'page=1.5', 'page=3abc', 'page=1e3', 'page='])(
    'трактует мусорное значение "%s" как первую страницу',
    async query => {
      resetSearchParams(query);

      render(<CatalogPage />);

      await waitFor(() => {
        expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
      });
    }
  );

  it.each(['page=1', 'page=01', 'page=abc', 'page=0', 'page='])(
    'убирает неканоничный "%s" из URL через replace',
    async query => {
      resetSearchParams(query);

      render(<CatalogPage />);

      await waitFor(() => {
        expect(lastNavigationUrl()).toBe('/catalog');
      });
      // replace, а не push: канонизация внешней ссылки не плодит историю
      expect(lastNavigation()?.type).toBe('replace');
      expect(mockPush).not.toHaveBeenCalled();
      await waitFor(() => {
        expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
      });
      expect(productsService.getAll).toHaveBeenCalledTimes(1);
    }
  );

  it('при канонизации первой страницы удаляет только page', async () => {
    resetSearchParams('category=sport&page=1');

    render(<CatalogPage />);

    await waitFor(() => {
      expect(lastNavigationUrl()).toBe('/catalog?category=sport');
    });
    expect(lastNavigation()?.type).toBe('replace');
  });

  it('не трогает URL, когда page уже канонична', async () => {
    render(<CatalogPage />);

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
    });
    expect(lastNavigation()).toBeNull();
  });

  it('откатывается на первую страницу через replace, когда API отдаёт 404', async () => {
    resetSearchParams('page=999');
    (productsService.getAll as Mock)
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValue(buildProductsResponse(24));

    render(<CatalogPage />);

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
    });
    expect(screen.queryByText('Не удалось загрузить товары')).not.toBeInTheDocument();
    // replace, а не push: иначе «назад» возвращает на битую страницу
    expect(mockReplace).toHaveBeenCalledWith('/catalog', expect.anything());
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('показывает ошибку, если 404 пришёл уже на первой странице', async () => {
    (productsService.getAll as Mock).mockRejectedValue({ response: { status: 404 } });

    render(<CatalogPage />);

    await waitFor(() => {
      expect(screen.getByText('Не удалось загрузить товары')).toBeInTheDocument();
    });
  });

  it('подхватывает страницу из URL при навигации «назад»', async () => {
    resetSearchParams('page=3');

    const { rerender } = render(<CatalogPage />);

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 3 }));
    });

    // Кнопка «назад»: URL сменился, компонент остался смонтированным
    resetSearchParams('page=2');
    rerender(<CatalogPage />);

    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }));
    });
  });

  it('не выдёргивает пользователя с новой страницы устаревшим 404', async () => {
    let rejectStale: (reason: unknown) => void = () => {};
    const stalePageThree = new Promise<never>((_, reject) => {
      rejectStale = reject;
    });
    // Ответ по 3-й странице «зависает» и провалится 404 уже после того,
    // как пользователь ушёл на 2-ю
    (productsService.getAll as Mock).mockImplementation((filters: { page?: number }) =>
      filters.page === 3 ? stalePageThree : Promise.resolve(buildProductsResponse(40))
    );

    render(<CatalogPage />);

    const pageThree = await screen.findByRole('button', { name: '3' });
    await act(async () => {
      pageThree.click();
    });
    await waitFor(() => {
      expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 3 }));
    });
    // История вызовов до критической секции неинтересна: запрос 1-й страницы
    // при монтировании легитимен, проверяем только последствия устаревшего 404
    (productsService.getAll as Mock).mockClear();
    mockReplace.mockClear();

    // Гонка из находки ревью: 404 по прежней странице приходит уже после того,
    // как пользователь ушёл на другую. В React 19 и сам дискретный клик
    // обрабатывается микрозадачей, поэтому продолжение упавшего запроса
    // успевает отработать даже ДО commit нового page — инвалидации по commit
    // (layout-эффект) для этого мало, версия обязана расти уже в момент
    // намерения пользователя, в обработчике события.
    //
    // act-окружение отключаем намеренно: под act клик, рендер и эффекты
    // сливаются в одну очередь и гонки нет. Порядок задан явно (отказ → один
    // microtask hop → клик), чтобы продолжение catch гарантированно опередило
    // микрозадачу React, а не зависело от деталей его планировщика.
    const actGlobal = globalThis as typeof globalThis & {
      IS_REACT_ACT_ENVIRONMENT?: boolean;
    };
    const prevActEnv = actGlobal.IS_REACT_ACT_ENVIRONMENT;
    actGlobal.IS_REACT_ACT_ENVIRONMENT = false;
    try {
      rejectStale({ response: { status: 404 } });
      // Один hop: реакция Promise.all уже отработала, продолжение catch стоит
      // следующим в очереди — клик вклинивается ровно перед ним
      await Promise.resolve();
      screen.getByRole('button', { name: '2' }).click();

      await waitFor(() => {
        expect(productsService.getAll).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }));
      });
    } finally {
      actGlobal.IS_REACT_ACT_ENVIRONMENT = prevActEnv;
    }

    // Устаревший 404 не откатывает ни состояние, ни URL
    expect(screen.getByRole('button', { name: '2' })).toHaveAttribute('aria-current', 'page');
    expect(productsService.getAll).not.toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
    expect(mockReplace).not.toHaveBeenCalled();
    expect(lastNavigationUrl()).toBe('/catalog?page=2');
  });
});
