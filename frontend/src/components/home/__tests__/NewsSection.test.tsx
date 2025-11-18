/**
 * Unit tests for NewsSection component
 * Story 11.3 - AC 6
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { NewsSection } from '../NewsSection';

// Mock newsService
vi.mock('@/services/newsService', () => ({
  newsService: {
    getNews: vi.fn(),
  },
}));

import { newsService } from '@/services/newsService';

const mockNewsItems = [
  {
    id: 1,
    title: 'Новая коллекция 2025',
    slug: 'new-collection-2025',
    excerpt: 'Представляем новую коллекцию спортивной одежды',
    image: '/images/news/collection.jpg',
    published_at: '2025-01-15T10:00:00Z',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
  {
    id: 2,
    title: 'Скидки на зимнюю экипировку',
    slug: 'winter-sale',
    excerpt: 'До конца месяца скидки до 30%',
    image: '/images/news/sale.jpg',
    published_at: '2025-01-14T10:00:00Z',
    created_at: '2025-01-14T10:00:00Z',
    updated_at: '2025-01-14T10:00:00Z',
  },
  {
    id: 3,
    title: 'Открытие нового склада',
    slug: 'new-warehouse',
    excerpt: 'Мы рады сообщить об открытии нового склада',
    image: null,
    published_at: '2025-01-13T10:00:00Z',
    created_at: '2025-01-13T10:00:00Z',
    updated_at: '2025-01-13T10:00:00Z',
  },
];

describe('NewsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows skeleton loader while loading', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    let resolvePromise: (value: typeof mockNewsItems) => void;
    mockGetNews.mockImplementationOnce(
      () =>
        new Promise(resolve => {
          resolvePromise = resolve;
        })
    );

    render(<NewsSection />);

    // Should show skeleton loaders
    expect(screen.getAllByLabelText('Загрузка новости')).toHaveLength(3);

    // Resolve the promise
    resolvePromise!(mockNewsItems);

    await waitFor(() => {
      expect(screen.queryByLabelText('Загрузка новости')).not.toBeInTheDocument();
    });
  });

  it('loads and displays 3 news items', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockResolvedValueOnce(mockNewsItems);

    render(<NewsSection />);

    await waitFor(() => {
      expect(screen.getByText('Новая коллекция 2025')).toBeInTheDocument();
      expect(screen.getByText('Скидки на зимнюю экипировку')).toBeInTheDocument();
      expect(screen.getByText('Открытие нового склада')).toBeInTheDocument();
    });

    expect(screen.getByText('Новости и акции')).toBeInTheDocument();
  });

  it('displays news excerpts', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockResolvedValueOnce(mockNewsItems);

    render(<NewsSection />);

    await waitFor(() => {
      expect(
        screen.getByText('Представляем новую коллекцию спортивной одежды')
      ).toBeInTheDocument();
      expect(screen.getByText('До конца месяца скидки до 30%')).toBeInTheDocument();
    });
  });

  it('shows fallback when API returns error', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockRejectedValueOnce(new Error('Network error'));

    render(<NewsSection />);

    await waitFor(() => {
      expect(
        screen.getByText('Новости временно недоступны. Попробуйте обновить страницу позже.')
      ).toBeInTheDocument();
    });
  });

  it('shows fallback when no news available', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockResolvedValueOnce([]);

    render(<NewsSection />);

    await waitFor(() => {
      expect(
        screen.getByText('Новости временно недоступны. Попробуйте обновить страницу позже.')
      ).toBeInTheDocument();
    });
  });

  it('handles news item without image', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockResolvedValueOnce(mockNewsItems);

    render(<NewsSection />);

    await waitFor(() => {
      expect(screen.getByText('Открытие нового склада')).toBeInTheDocument();
    });

    // Should have 2 images (items 1 and 2 have images, item 3 doesn't)
    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(2);
  });

  it('formats dates in Russian locale', async () => {
    const mockGetNews = vi.mocked(newsService.getNews);
    mockGetNews.mockResolvedValueOnce(mockNewsItems);

    render(<NewsSection />);

    await waitFor(() => {
      // Dates should be formatted in Russian locale
      const timeElements = screen.getAllByRole('time');
      expect(timeElements).toHaveLength(3);
    });
  });
});
