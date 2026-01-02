/* eslint-disable @next/next/no-img-element */
/**
 * Electric Orange Product Card Component
 *
 * Product Card for catalog and homepage
 ...
 */

'use client';

import React from 'react';
import { cn } from '@/utils/cn';
import { ElectricBadge } from '../Badge';

// ... (Types remain same)

// ============================================
// Product Card Component
// ============================================

export function ElectricProductCard({
  // id, // Removed unused id
  image,
  title,
  brand,
  price,
  oldPrice,
  badge,
  isFavorite = false,
  inStock = true,
  onAddToCart,
  onToggleFavorite,
  onClick,
  className,
}: ElectricProductCardProps) {
  const handleCardClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    // Prevent navigation if clicking on buttons
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    onClick?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleCardClick(e);
    }
  };

  return (
    <article
      className={cn(
        // Base - Rectangular card
        'bg-[#1A1A1A] border border-[#333333] p-4',
        'transition-all duration-300',
        'hover:border-[#FF6B00] hover:shadow-[0_0_20px_rgba(255,107,0,0.15)]',
        'cursor-pointer group',
        !inStock && 'opacity-60',
        className
      )}
      onClick={handleCardClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      {/* Image Container */}
      <div className="relative aspect-square bg-[#2A2A2A] mb-4 overflow-hidden">
        <img
          src={image}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />

        {/* Badge */}
        {badge && (
          <div className="absolute top-2 left-2 z-10">
            <ElectricBadge variant={badge}>
              {badge === 'hit'
                ? 'Хит'
                : badge === 'sale'
                  ? `-${Math.round(((oldPrice! - price) / oldPrice!) * 100)}%`
                  : 'New'}
            </ElectricBadge>
          </div>
        )}

        {/* Favorite Button */}
        <button
          onClick={e => {
            e.stopPropagation();
            onToggleFavorite?.();
          }}
          className={cn(
            'absolute top-2 right-2 z-10 w-8 h-8 flex items-center justify-center',
            'transition-colors duration-200',
            isFavorite ? 'text-[#FF6B00]' : 'text-[#666666] hover:text-[#FF6B00]'
          )}
          aria-label={isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'}
        >
          {isFavorite ? '♥' : '♡'}
        </button>

        {/* Out of Stock Overlay */}
        {!inStock && (
          <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
            <span className="text-[#A0A0A0] font-medium uppercase">Нет в наличии</span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="space-y-2">
        {/* Brand */}
        {brand && (
          <p
            className="text-xs text-[#A0A0A0] uppercase tracking-wide"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            {brand}
          </p>
        )}

        {/* Title */}
        <h3
          className="text-white font-medium line-clamp-2 min-h-[48px]"
          style={{ fontFamily: "'Inter', sans-serif" }}
        >
          {title}
        </h3>

        {/* Price - Skewed */}
        <div className="flex items-center gap-2">
          <span
            className="text-xl font-bold text-[#FF6B00] inline-block"
            style={{
              fontFamily: "'Roboto Condensed', sans-serif",
              transform: 'skewX(-12deg)',
            }}
          >
            <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>
              {formatPrice(price)} ₽
            </span>
          </span>
          {oldPrice && (
            <span className="text-sm text-[#666666] line-through">{formatPrice(oldPrice)} ₽</span>
          )}
        </div>
      </div>

      {/* Action Buttons Row - Always visible per spec: Primary + Outline */}
      <div className="flex gap-2.5 mt-4">
        {/* Primary Button: Add to Cart */}
        <button
          onClick={e => {
            e.stopPropagation();
            onAddToCart?.();
          }}
          disabled={!inStock}
          className={cn(
            'flex-1 h-10 font-semibold uppercase text-sm tracking-wide',
            'transition-all duration-300',
            inStock
              ? 'bg-[#FF6B00] text-black hover:bg-white hover:text-[#FF6B00]'
              : 'bg-[#333333] text-[#666666] cursor-not-allowed'
          )}
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>В КОРЗИНУ</span>
        </button>

        {/* Outline Button: Wishlist */}
        <button
          onClick={e => {
            e.stopPropagation();
            onToggleFavorite?.();
          }}
          className={cn(
            'flex-1 h-10 font-semibold uppercase text-sm tracking-wide',
            'transition-all duration-300',
            'bg-transparent border-2',
            isFavorite
              ? 'border-[#FF6B00] text-[#FF6B00]'
              : 'border-white text-white hover:border-[#FF6B00] hover:text-[#FF6B00]'
          )}
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>ЗАПОМНИТЬ</span>
        </button>
      </div>
    </article>
  );
}

export default ElectricProductCard;
