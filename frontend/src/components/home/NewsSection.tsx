/**
 * NewsSection Component (Story 12.7)
 * Блок "Наш блог" на главной странице
 */

'use client';

import React from 'react';
import { BlogPostCard } from './BlogPostCard';
import { MOCK_BLOG_POSTS } from '@/__mocks__/blogPosts';

export const NewsSection: React.FC = () => {
  if (!MOCK_BLOG_POSTS || MOCK_BLOG_POSTS.length === 0) {
    return null;
  }

  return (
    <section className="max-w-[1280px] mx-auto px-3 md:px-4 lg:px-6" aria-labelledby="blog-heading">
      {/* Заголовок секции */}
      <h2 id="blog-heading" className="text-3xl font-bold mb-8 text-primary">
        Наш блог
      </h2>

      {/* Grid статей */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {MOCK_BLOG_POSTS.map(post => (
          <BlogPostCard
            key={post.id}
            id={post.id}
            title={post.title}
            excerpt={post.excerpt}
            image={post.image}
            date={post.date}
            slug={post.slug}
          />
        ))}
      </div>
    </section>
  );
};

NewsSection.displayName = 'NewsSection';
