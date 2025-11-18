/**
 * NewsSection Component
 * Блок новостей и акций
 *
 * @see Story 11.3 - AC 3, 5
 */

'use client';

import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import { Card } from '@/components/ui/Card';
import { newsService } from '@/services/newsService';
import { NewsSkeletonLoader } from '@/components/common/NewsSkeletonLoader';
import { NewsFallback } from '@/components/common/NewsFallback';
import type { NewsItem } from '@/types/api';

export const NewsSection: React.FC = () => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const data = await newsService.getNews({ page_size: 3 });
        setNews(data);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  if (loading) {
    return <NewsSkeletonLoader />;
  }

  if (error || news.length === 0) {
    return <NewsFallback />;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold text-text-primary">Новости и акции</h3>
      <div className="grid gap-4">
        {news.map(item => (
          <Card key={item.id} hover className="p-4">
            <div className="flex gap-4">
              {item.image && (
                <div className="relative w-24 h-24 shrink-0">
                  <Image
                    src={item.image}
                    alt={item.title}
                    fill
                    className="object-cover rounded-lg"
                  />
                </div>
              )}
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-text-primary mb-1">{item.title}</h4>
                <p className="text-sm text-text-secondary mb-2 line-clamp-2">{item.excerpt}</p>
                <time className="text-xs text-text-muted" dateTime={item.published_at}>
                  {new Date(item.published_at).toLocaleDateString('ru-RU')}
                </time>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
