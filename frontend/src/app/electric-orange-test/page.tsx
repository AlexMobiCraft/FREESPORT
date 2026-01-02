'use client';

/**
 * Electric Orange Design System Test Page
 *
 * URL: /electric-orange-test
 *
 * Эта страница демонстрирует все компоненты дизайн-системы Electric Orange:
 * - Typography (Display, Headline, Body)
 * - Buttons (Primary, Outline, Ghost)
 * - Inputs (Default, Focus, Error)
 * - Badges (Primary, Sale, New, Hit)
 * - Cards (Product, Category)
 * - Skew geometry demo
 */

import React, { useState } from 'react';

export default function ElectricOrangeTestPage() {
  const [inputValue, setInputValue] = useState('');
  const [checkboxChecked, setCheckboxChecked] = useState(false);

  return (
    <div className="min-h-screen bg-[#0F0F0F] text-white p-8">
      {/* Page Header */}
      <header className="mb-16 border-b border-[#333333] pb-8">
        <h1
          className="text-5xl font-black uppercase mb-4"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>
            Electric Orange
          </span>
        </h1>
        <p className="text-[#A0A0A0]">
          Design System Test Page • Digital Brutalism & Kinetic Energy
        </p>
      </header>

      {/* Color Palette */}
      <section className="mb-16">
        <SectionHeader>Цветовая палитра</SectionHeader>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <ColorSwatch color="#FF6B00" name="Primary" />
          <ColorSwatch color="#FF8533" name="Primary Hover" />
          <ColorSwatch color="#E55A00" name="Primary Active" />
          <ColorSwatch color="#0F0F0F" name="BG Body" border />
          <ColorSwatch color="#1A1A1A" name="BG Card" border />
          <ColorSwatch color="#333333" name="Border" border />
          <ColorSwatch color="#FFFFFF" name="Text Primary" border />
          <ColorSwatch color="#A0A0A0" name="Text Secondary" border />
          <ColorSwatch color="#666666" name="Text Muted" border />
          <ColorSwatch color="#22C55E" name="Success" />
          <ColorSwatch color="#EAB308" name="Warning" />
          <ColorSwatch color="#EF4444" name="Danger" />
        </div>
      </section>

      {/* Typography */}
      <section className="mb-16">
        <SectionHeader>Типография</SectionHeader>

        <div className="space-y-8 bg-[#1A1A1A] p-8 border border-[#333333]">
          {/* Display - Skewed */}
          <div>
            <p className="text-[#666666] text-sm mb-2">
              Display XL (72px, Roboto Condensed, Skewed)
            </p>
            <h2
              className="text-6xl font-black uppercase text-white"
              style={{
                fontFamily: "'Roboto Condensed', sans-serif",
                transform: 'skewX(-12deg)',
              }}
            >
              <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>
                Преодолей границы
              </span>
            </h2>
          </div>

          {/* Headline - Skewed */}
          <div>
            <p className="text-[#666666] text-sm mb-2">
              Headline L (36px, Roboto Condensed, Skewed)
            </p>
            <h3
              className="text-4xl font-bold uppercase text-white"
              style={{
                fontFamily: "'Roboto Condensed', sans-serif",
                transform: 'skewX(-12deg)',
              }}
            >
              <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>
                Хиты продаж
              </span>
            </h3>
          </div>

          {/* Title - Straight */}
          <div>
            <p className="text-[#666666] text-sm mb-2">Title L (24px, Inter, Straight)</p>
            <h4 className="text-2xl font-semibold text-white">Перчатки боксерские BOYBO STAIN</h4>
          </div>

          {/* Body - Straight */}
          <div>
            <p className="text-[#666666] text-sm mb-2">Body M (16px, Inter, Straight)</p>
            <p className="text-base text-[#A0A0A0]">
              Боксерские перчатки BOYBO STAIN — профессиональный выбор для тренировок и
              соревнований. Изготовлены из высококачественной синтетической кожи.
            </p>
          </div>

          {/* Price - Skewed */}
          <div>
            <p className="text-[#666666] text-sm mb-2">Price Tag (Skewed, Orange)</p>
            <span
              className="text-3xl font-bold text-[#FF6B00] inline-block"
              style={{
                fontFamily: "'Roboto Condensed', sans-serif",
                transform: 'skewX(-12deg)',
              }}
            >
              <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>7 990 ₽</span>
            </span>
          </div>
        </div>
      </section>

      {/* Buttons */}
      <section className="mb-16">
        <SectionHeader>Кнопки</SectionHeader>

        <div className="space-y-8 bg-[#1A1A1A] p-8 border border-[#333333]">
          {/* Primary Buttons */}
          <div>
            <p className="text-[#666666] text-sm mb-4">Primary (Skewed, Orange)</p>
            <div className="flex flex-wrap gap-4">
              <SkewedButton variant="primary" size="sm">
                Small
              </SkewedButton>
              <SkewedButton variant="primary" size="md">
                Medium
              </SkewedButton>
              <SkewedButton variant="primary" size="lg">
                Large
              </SkewedButton>
            </div>
          </div>

          {/* Outline Buttons */}
          <div>
            <p className="text-[#666666] text-sm mb-4">Outline (Skewed, White Border)</p>
            <div className="flex flex-wrap gap-4">
              <SkewedButton variant="outline" size="sm">
                Small
              </SkewedButton>
              <SkewedButton variant="outline" size="md">
                Medium
              </SkewedButton>
              <SkewedButton variant="outline" size="lg">
                Large
              </SkewedButton>
            </div>
          </div>

          {/* Ghost Buttons */}
          <div>
            <p className="text-[#666666] text-sm mb-4">Ghost (Skewed, Transparent)</p>
            <div className="flex flex-wrap gap-4">
              <SkewedButton variant="ghost" size="sm">
                Small
              </SkewedButton>
              <SkewedButton variant="ghost" size="md">
                Medium
              </SkewedButton>
              <SkewedButton variant="ghost" size="lg">
                Large
              </SkewedButton>
            </div>
          </div>

          {/* CTA Example */}
          <div>
            <p className="text-[#666666] text-sm mb-4">CTA Example</p>
            <div className="flex gap-4">
              <SkewedButton variant="primary" size="lg">
                Добавить в корзину
              </SkewedButton>
              <SkewedButton variant="outline" size="lg">
                ♡
              </SkewedButton>
            </div>
          </div>
        </div>
      </section>

      {/* Form Elements */}
      <section className="mb-16">
        <SectionHeader>Форма</SectionHeader>

        <div className="bg-[#1A1A1A] p-8 border border-[#333333]">
          <div className="max-w-md space-y-6">
            {/* Text Input */}
            <div>
              <label className="block text-[#A0A0A0] text-sm mb-2">Имя</label>
              <input
                type="text"
                placeholder="Введите имя"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                className="w-full h-11 px-4 bg-transparent border border-[#333333] text-white placeholder-[#666666] focus:border-[#FF6B00] focus:outline-none transition-colors"
              />
            </div>

            {/* Input with error */}
            <div>
              <label className="block text-[#A0A0A0] text-sm mb-2">Email (с ошибкой)</label>
              <input
                type="email"
                placeholder="Введите email"
                className="w-full h-11 px-4 bg-transparent border border-[#EF4444] text-white placeholder-[#666666] focus:outline-none"
              />
              <p className="text-[#EF4444] text-sm mt-1">Некорректный email</p>
            </div>

            {/* Checkbox */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setCheckboxChecked(!checkboxChecked)}
                className={`w-5 h-5 border-2 flex items-center justify-center transition-colors ${
                  checkboxChecked
                    ? 'bg-[#FF6B00] border-[#FF6B00]'
                    : 'border-[#333333] hover:border-[#FF6B00]'
                }`}
                style={{ transform: 'skewX(-12deg)' }}
              >
                {checkboxChecked && (
                  <span
                    className="text-black text-xs font-bold"
                    style={{ transform: 'skewX(12deg)' }}
                  >
                    ✓
                  </span>
                )}
              </button>
              <span className="text-white">Согласен с условиями</span>
            </div>
          </div>
        </div>
      </section>

      {/* Badges */}
      <section className="mb-16">
        <SectionHeader>Бейджи</SectionHeader>

        <div className="bg-[#1A1A1A] p-8 border border-[#333333]">
          <div className="flex flex-wrap gap-4">
            <SkewedBadge variant="primary">Новинка</SkewedBadge>
            <SkewedBadge variant="sale">-20%</SkewedBadge>
            <SkewedBadge variant="hit">Хит</SkewedBadge>
            <SkewedBadge variant="new">New</SkewedBadge>
          </div>
        </div>
      </section>

      {/* Product Card Demo */}
      <section className="mb-16">
        <SectionHeader>Карточка товара</SectionHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <ProductCardDemo
            brand="BOYBO"
            title="Перчатки боксерские STAIN"
            price="7 990"
            badge="hit"
          />
          <ProductCardDemo
            brand="Nike"
            title="Футболка Pro Training"
            price="4 990"
            oldPrice="6 990"
            badge="sale"
          />
          <ProductCardDemo
            brand="Adidas"
            title="Кроссовки Ultraboost 22"
            price="14 990"
            badge="new"
          />
          <ProductCardDemo brand="VECTOR" title="Спортивная куртка WindBreaker" price="8 990" />
        </div>
      </section>

      {/* Category Card Demo */}
      <section className="mb-16">
        <SectionHeader>Карточка категории</SectionHeader>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <CategoryCardDemo title="Единоборства" />
          <CategoryCardDemo title="Фитнес" />
          <CategoryCardDemo title="Игровые виды" />
          <CategoryCardDemo title="Оборудование" />
        </div>
      </section>

      {/* Glow Effects */}
      <section className="mb-16">
        <SectionHeader>Эффекты свечения</SectionHeader>

        <div className="bg-[#1A1A1A] p-8 border border-[#333333]">
          <div className="flex flex-wrap gap-8 items-center justify-center">
            <div
              className="w-32 h-32 bg-[#FF6B00] flex items-center justify-center"
              style={{
                boxShadow: '0 0 30px rgba(255, 107, 0, 0.5)',
                animation: 'pulse 2s ease-in-out infinite',
              }}
            >
              <span className="text-black font-bold">GLOW</span>
            </div>

            <div className="w-32 h-32 border-2 border-[#FF6B00] flex items-center justify-center transition-shadow hover:shadow-[0_0_40px_rgba(255,107,0,0.5)]">
              <span className="text-[#FF6B00] font-bold">HOVER</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#333333] pt-8 text-center text-[#666666]">
        <p>Electric Orange Design System v1.0 • FREESPORT</p>
        <p className="mt-2">Digital Brutalism & Kinetic Energy</p>
      </footer>

      <style jsx>{`
        @keyframes pulse {
          0%,
          100% {
            box-shadow: 0 0 20px rgba(255, 107, 0, 0.3);
          }
          50% {
            box-shadow: 0 0 40px rgba(255, 107, 0, 0.6);
          }
        }
      `}</style>
    </div>
  );
}

// ============================================
// Helper Components
// ============================================

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="text-2xl font-bold uppercase text-white mb-6 inline-block pb-2 border-b-[3px] border-[#FF6B00]"
      style={{
        fontFamily: "'Roboto Condensed', sans-serif",
        transform: 'skewX(-12deg)',
      }}
    >
      <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{children}</span>
    </h2>
  );
}

function ColorSwatch({ color, name, border }: { color: string; name: string; border?: boolean }) {
  return (
    <div className="text-center">
      <div
        className={`w-full h-16 mb-2 ${border ? 'border border-[#333333]' : ''}`}
        style={{ backgroundColor: color }}
      />
      <p className="text-xs text-[#A0A0A0]">{name}</p>
      <p className="text-xs text-[#666666]">{color}</p>
    </div>
  );
}

interface SkewedButtonProps {
  variant: 'primary' | 'outline' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

function SkewedButton({ variant, size, children }: SkewedButtonProps) {
  const sizeClasses = {
    sm: 'h-9 px-4 text-sm',
    md: 'h-11 px-6 text-base',
    lg: 'h-14 px-8 text-lg',
  };

  const variantClasses = {
    primary:
      'bg-[#FF6B00] text-black hover:bg-[#FF8533] hover:shadow-[0_0_20px_rgba(255,107,0,0.4)]',
    outline:
      'bg-transparent border-2 border-white text-white hover:border-[#FF6B00] hover:text-[#FF6B00]',
    ghost: 'bg-transparent text-white hover:text-[#FF6B00] hover:bg-[rgba(255,107,0,0.1)]',
  };

  return (
    <button
      className={`font-semibold uppercase transition-all ${sizeClasses[size]} ${variantClasses[variant]}`}
      style={{ transform: 'skewX(-12deg)' }}
    >
      <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{children}</span>
    </button>
  );
}

interface SkewedBadgeProps {
  variant: 'primary' | 'sale' | 'hit' | 'new';
  children: React.ReactNode;
}

function SkewedBadge({ variant, children }: SkewedBadgeProps) {
  const variantClasses = {
    primary: 'bg-[#FF6B00] text-black',
    sale: 'bg-[#EF4444] text-white',
    hit: 'bg-[#22C55E] text-black',
    new: 'bg-[#FF6B00] text-black',
  };

  return (
    <span
      className={`inline-flex px-3 py-1 text-xs font-bold uppercase ${variantClasses[variant]}`}
      style={{
        fontFamily: "'Roboto Condensed', sans-serif",
        transform: 'skewX(-12deg)',
      }}
    >
      <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{children}</span>
    </span>
  );
}

interface ProductCardDemoProps {
  brand: string;
  title: string;
  price: string;
  oldPrice?: string;
  badge?: 'hit' | 'sale' | 'new';
}

function ProductCardDemo({ brand, title, price, oldPrice, badge }: ProductCardDemoProps) {
  return (
    <div className="bg-[#1A1A1A] border border-[#333333] p-4 transition-all hover:border-[#FF6B00] hover:shadow-[0_0_20px_rgba(255,107,0,0.15)] group">
      {/* Image placeholder */}
      <div className="relative aspect-square bg-[#2A2A2A] mb-4 flex items-center justify-center">
        <span className="text-[#555555]">IMG</span>
        {badge && (
          <div className="absolute top-2 left-2">
            <SkewedBadge variant={badge}>
              {badge === 'hit' ? 'Хит' : badge === 'sale' ? '-20%' : 'New'}
            </SkewedBadge>
          </div>
        )}
        <button className="absolute top-2 right-2 text-[#666666] hover:text-[#FF6B00] transition-colors">
          ♡
        </button>
      </div>

      {/* Info */}
      <p className="text-xs text-[#A0A0A0] uppercase mb-1">{brand}</p>
      <h3 className="text-white font-medium mb-3 line-clamp-2">{title}</h3>

      {/* Price */}
      <div className="flex items-center gap-2 mb-4">
        <span
          className="text-xl font-bold text-[#FF6B00]"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{price} ₽</span>
        </span>
        {oldPrice && <span className="text-sm text-[#666666] line-through">{oldPrice} ₽</span>}
      </div>

      {/* Button */}
      <SkewedButton variant="primary" size="sm">
        В корзину
      </SkewedButton>
    </div>
  );
}

function CategoryCardDemo({ title }: { title: string }) {
  return (
    <div className="relative aspect-square bg-[#2A2A2A] overflow-hidden group cursor-pointer">
      {/* Image placeholder with grayscale effect */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/80" />

      {/* Title */}
      <div className="absolute bottom-0 left-0 right-0 p-4">
        <h3
          className="text-xl font-bold uppercase text-white"
          style={{
            fontFamily: "'Roboto Condensed', sans-serif",
            transform: 'skewX(-12deg)',
          }}
        >
          <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{title}</span>
        </h3>
      </div>

      {/* Hover flash effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[rgba(255,107,0,0.3)] to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-500" />
    </div>
  );
}
