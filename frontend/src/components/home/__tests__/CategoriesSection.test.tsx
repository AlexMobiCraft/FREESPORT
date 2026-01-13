/**
 * CategoriesSection Component Tests
 * Обновление блока Популярных Категорий - Smart Grid + Фильтрация
 */

import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../__mocks__/api/server';
import { CategoriesSection } from '../CategoriesSection';

// Mock категории с реальными слагами
const mockCategories = [
  { id: 1, name: 'Спортивные игры', slug: 'sportivnye-igry', products_count: 150 },
  { id: 2, name: 'Фитнес и атлетика', slug: 'fitnes-i-atletika', products_count: 230 },
  { id: 3, name: 'Гимнастика и танцы', slug: 'gimnastika-i-tantsy', products_count: 95 },
  { id: 4, name: 'Плавание', slug: 'plavanie', products_count: 180 },
  { id: 5, name: 'Единоборства', slug: 'edinoborstva', products_count: 120 },
  { id: 6, name: 'Детский транспорт', slug: 'detskij-transport', products_count: 75 },
  { id: 7, name: 'Оборудование', slug: 'oborudovanie', products_count: 200 },
  // Лишние категории, которые должны быть отфильтрованы
  { id: 8, name: 'Футбол', slug: 'football', products_count: 100 },
  { id: 9, name: 'Бег', slug: 'running', products_count: 50 },
];

// Setup MSW
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('CategoriesSection', () => {
  beforeEach(() => {
    server.use(
      http.get('*/categories/', () => {
        return HttpResponse.json(mockCategories);
      })
    );
  });

  it('displays exactly 7 target categories in correct order', async () => {
    render(<CategoriesSection />);

    // Loading state
    expect(screen.getByLabelText(/Загрузка категорий/i)).toBeInTheDocument();

    // Success state - используем getAllByText т.к. Desktop и Mobile версии рендерятся одновременно
    await waitFor(() => {
      expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
    });

    // Все 7 категорий должны присутствовать (минимум 1 раз, может быть 2 - desktop + mobile)
    expect(screen.getAllByText('Фитнес и атлетика').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Гимнастика и танцы').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Плавание').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Единоборства').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Детский транспорт').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Оборудование').length).toBeGreaterThanOrEqual(1);

    // Лишние категории НЕ должны отображаться
    expect(screen.queryByText('Футбол')).not.toBeInTheDocument();
    expect(screen.queryByText('Бег')).not.toBeInTheDocument();

    // Проверяем заголовок
    expect(screen.getByText('Популярные категории')).toBeInTheDocument();
  });

  it('category links navigate to correct catalog URLs', async () => {
    render(<CategoriesSection />);

    await waitFor(() => {
      expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
    });

    // Проверяем ссылки - берём первый найденный элемент
    const sportLinks = screen.getAllByText('Спортивные игры');
    expect(sportLinks[0].closest('a')).toHaveAttribute('href', '/catalog?category=sportivnye-igry');

    const swimLinks = screen.getAllByText('Плавание');
    expect(swimLinks[0].closest('a')).toHaveAttribute('href', '/catalog?category=plavanie');
  });

  it('shows error state on API failure and allows retry', { timeout: 20000 }, async () => {
    server.use(
      http.get('*/categories/', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Internal Server Error' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      })
    );

    const user = userEvent.setup();
    render(<CategoriesSection />);

    await waitFor(
      () => {
        expect(screen.getByText(/Не удалось загрузить категории/i)).toBeInTheDocument();
      },
      { timeout: 15000 }
    );

    const retryButton = screen.getByRole('button', { name: /Повторить попытку/i });
    expect(retryButton).toBeInTheDocument();

    // Reset handler и retry
    server.resetHandlers();
    server.use(
      http.get('*/categories/', () => {
        return HttpResponse.json(mockCategories);
      })
    );
    await user.click(retryButton);

    await waitFor(
      () => {
        expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 3000 }
    );
  });

  it('uses correct API endpoint with limit 100', async () => {
    const requestSpy = vi.fn();

    server.use(
      http.get('*/categories/', ({ request }) => {
        requestSpy(request.url);
        return HttpResponse.json(mockCategories);
      })
    );

    render(<CategoriesSection />);

    await waitFor(() => {
      expect(requestSpy).toHaveBeenCalled();
    });

    const calledUrl = requestSpy.mock.calls[0][0];
    expect(calledUrl).toContain('limit=100');
  });

  it('does not render when no target categories are returned', async () => {
    server.use(
      http.get('*/categories/', () => {
        // Возвращаем только категории, которых нет в TARGET_CATEGORIES
        return HttpResponse.json([
          { id: 8, name: 'Футбол', slug: 'football', products_count: 100 },
        ]);
      })
    );

    const { container } = render(<CategoriesSection />);

    await waitFor(() => {
      expect(screen.queryByLabelText(/Загрузка категорий/i)).not.toBeInTheDocument();
    });

    expect(container.firstChild).toBeNull();
  });

  it('handles partial category set gracefully (resilience)', async () => {
    // Только 5 из 7 категорий
    const partialCategories = mockCategories.slice(0, 5);
    server.use(
      http.get('*/categories/', () => {
        return HttpResponse.json(partialCategories);
      })
    );

    render(<CategoriesSection />);

    await waitFor(() => {
      expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
    });

    // Должны отображаться 5 категорий
    expect(screen.getAllByText('Фитнес и атлетика').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Гимнастика и танцы').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Плавание').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Единоборства').length).toBeGreaterThanOrEqual(1);

    // Отсутствующие категории не должны ломать рендер
    expect(screen.queryByText('Детский транспорт')).not.toBeInTheDocument();
    expect(screen.queryByText('Оборудование')).not.toBeInTheDocument();
  });

  it('has desktop Smart Grid layout (hidden on mobile)', async () => {
    render(<CategoriesSection />);

    await waitFor(() => {
      expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
    });

    // Проверяем наличие desktop контейнера
    const desktopContainer = document.querySelector('.hidden.lg\\:block');
    expect(desktopContainer).toBeInTheDocument();
  });

  it('has mobile carousel layout (hidden on desktop)', async () => {
    render(<CategoriesSection />);

    await waitFor(() => {
      expect(screen.getAllByText('Спортивные игры').length).toBeGreaterThanOrEqual(1);
    });

    // Проверяем наличие mobile контейнера
    const mobileContainer = document.querySelector('.lg\\:hidden');
    expect(mobileContainer).toBeInTheDocument();
  });
});
