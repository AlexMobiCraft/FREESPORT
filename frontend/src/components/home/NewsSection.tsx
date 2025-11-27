/**
 * NewsSection Component
 * Загружает новости из API /news и показывает fallback при недоступности
 */

'use client';

import React, { useEffect, useState } from 'react';
import { NewsCard } from './NewsCard';
import { newsService } from '@/services/newsService';
import type { NewsItem } from '@/types/api';
import { NewsSkeletonLoader } from '@/components/common/NewsSkeletonLoader';
import { NewsFallback } from '@/components/common/NewsFallback';
import { STATIC_NEWS_ITEMS } from '@/__mocks__/news';

interface NewsCardData {
  id: number;
  title: string;
  excerpt: string;
  image: string;
  publishedAt: string;
}

const getFallbackImage = (index: number): string => {
  return (
    STATIC_NEWS_ITEMS[index % STATIC_NEWS_ITEMS.length]?.image || '/images/new/running-shoes.jpg'
  );
};

const mapNewsItem = (item: NewsItem, index: number): NewsCardData => ({
  id: item.id,
  title: item.title,
  excerpt: item.excerpt,
  image: item.image || getFallbackImage(index),
  publishedAt: item.published_at,
});

const mapStaticItem = (item: (typeof STATIC_NEWS_ITEMS)[number]): NewsCardData => ({
  id: item.id,
  title: item.title,
  excerpt: item.excerpt,
  image: item.image,
  publishedAt: item.published_at,
});

export const NewsSection: React.FC = () => {
  const [newsItems, setNewsItems] = useState<NewsCardData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const fetchNews = async () => {
      try {
        setIsLoading(true);
        const data = await newsService.getNews({ page_size: 3 });

        if (!isMounted) return;

        if (data && data.length > 0) {
          setNewsItems(data.slice(0, 3).map(mapNewsItem));
        } else {
          setNewsItems(STATIC_NEWS_ITEMS.map(mapStaticItem));
        }
      } catch {
        if (!isMounted) return;
        setNewsItems(STATIC_NEWS_ITEMS.map(mapStaticItem));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchNews();

    return () => {
      isMounted = false;
    };
  }, []);

  const hasNews = newsItems.length > 0;

  return (
    <section className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6" aria-labelledby="news-heading">
      <h2 id="news-heading" className="text-3xl font-bold mb-8 text-text-primary">
        Новости
      </h2>

      {isLoading && <NewsSkeletonLoader />}

      {!isLoading && !hasNews && <NewsFallback />}

      {!isLoading && hasNews && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {newsItems.map(item => (
            <NewsCard
              key={item.id}
              title={item.title}
              excerpt={item.excerpt}
              image={item.image}
              publishedAt={item.publishedAt}
            />
          ))}
        </div>
      )}
    </section>
  );
};

NewsSection.displayName = 'NewsSection';
