/**
 * BlogSection Component
 * Загружает статьи блога из API /blog и показывает fallback при недоступности
 */

'use client';

import React, { useEffect, useState } from 'react';
import { BlogPostCard } from './BlogPostCard';
import { blogService } from '@/services/blogService';
import type { BlogItem } from '@/types/api';
import { NewsSkeletonLoader } from '@/components/common/NewsSkeletonLoader';
import { NewsFallback } from '@/components/common/NewsFallback';
import { MOCK_BLOG_POSTS } from '@/__mocks__/blogPosts';

interface BlogCardData {
  id: string;
  title: string;
  slug: string;
  excerpt: string;
  image: string;
  date: string;
}

const getFallbackImage = (index: number): string => {
  return MOCK_BLOG_POSTS[index % MOCK_BLOG_POSTS.length]?.image || '/images/new/running-shoes.jpg';
};

const mapBlogItem = (item: BlogItem, index: number): BlogCardData => ({
  id: String(item.id),
  title: item.title,
  slug: item.slug,
  excerpt: item.excerpt,
  image: item.image || getFallbackImage(index),
  date: item.published_at,
});

const mapStaticItem = (item: (typeof MOCK_BLOG_POSTS)[number]): BlogCardData => ({
  id: item.id,
  title: item.title,
  slug: item.slug,
  excerpt: item.excerpt,
  image: item.image,
  date: item.date,
});

export const BlogSection: React.FC = () => {
  const [blogItems, setBlogItems] = useState<BlogCardData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const fetchBlog = async () => {
      try {
        setIsLoading(true);
        const data = await blogService.getBlogPosts({ page_size: 3 });

        if (!isMounted) return;

        if (data && data.results && data.results.length > 0) {
          setBlogItems(data.results.slice(0, 3).map(mapBlogItem));
        } else {
          setBlogItems(MOCK_BLOG_POSTS.map(mapStaticItem));
        }
      } catch {
        if (!isMounted) return;
        setBlogItems(MOCK_BLOG_POSTS.map(mapStaticItem));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchBlog();

    return () => {
      isMounted = false;
    };
  }, []);

  const hasPosts = blogItems.length > 0;

  return (
    <section className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6" aria-labelledby="blog-heading">
      {/* Header */}
      <h2 id="blog-heading" className="text-3xl font-bold text-text-primary mb-8">
        Наш блог
      </h2>

      {isLoading && <NewsSkeletonLoader />}

      {!isLoading && !hasPosts && <NewsFallback />}

      {!isLoading && hasPosts && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {blogItems.map(item => (
            <BlogPostCard
              key={item.id}
              id={item.id}
              title={item.title}
              slug={item.slug}
              excerpt={item.excerpt}
              image={item.image}
              date={item.date}
            />
          ))}
        </div>
      )}
    </section>
  );
};

BlogSection.displayName = 'BlogSection';
