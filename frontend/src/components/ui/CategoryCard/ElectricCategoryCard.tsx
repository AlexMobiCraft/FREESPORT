/* eslint-disable @next/next/no-img-element */
/**
 * Electric Orange Category Card Component
 ...
 */

'use client';

import React from 'react';
import { cn } from '@/utils/cn';

// ... (Types remain same)

// ============================================
// Category Card Component
// ============================================

export function ElectricCategoryCard({
  // id, // Removed unused id
  title,
  image,
  productCount,
  href,
  onClick,
  aspectRatio = 'square',
  className,
}: ElectricCategoryCardProps) {
  const Component = href ? 'a' : 'div';
  const linkProps = href ? { href } : {};

  return (
    <Component
      {...linkProps}
      onClick={onClick}
      className={cn(
        'relative overflow-hidden group cursor-pointer block',
        aspectRatioStyles[aspectRatio],
        className
      )}
    >
      {/* Background Image with Grayscale Effect */}
      <img
        src={image}
        alt={title}
        className="absolute inset-0 w-full h-full object-cover
          grayscale group-hover:grayscale-0
          transition-all duration-300
          group-hover:scale-105"
        loading="lazy"
      />

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/80" />

      {/* Title Overlay */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6">
        <h3
          className="text-[1.8rem] font-black uppercase text-white tracking-wide"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
            textShadow: '2px 2px 0 #000',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{title}</span>
        </h3>

        {/* Product Count */}
        {productCount !== undefined && (
          <p className="text-[#A0A0A0] text-sm mt-1" style={{ fontFamily: "'Inter', sans-serif" }}>
            {productCount} товаров
          </p>
        )}

        {/* Arrow Indicator */}
        <div
          className="mt-2 text-[#FF6B00] font-bold uppercase text-sm opacity-0 group-hover:opacity-100 transition-opacity"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>Перейти →</span>
        </div>
      </div>

      {/* Orange Flash Effect on Hover */}
      <div
        className="absolute inset-0 pointer-events-none
          bg-gradient-to-r from-transparent via-[rgba(255,107,0,0.3)] to-transparent
          -translate-x-full group-hover:translate-x-full
          transition-transform duration-500 ease-out"
      />
    </Component>
  );
}

export default ElectricCategoryCard;
