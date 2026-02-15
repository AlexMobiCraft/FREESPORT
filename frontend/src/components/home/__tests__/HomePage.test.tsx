/**
 * HomePage integration test — AC1 regression: section order
 * Verifies MarketingBannersSection renders between QuickLinksSection and CategoriesSection
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { HomePage } from '../HomePage';

// Mock all section components as simple divs with data-testid
vi.mock('../HeroSection', () => ({ default: () => <div data-testid="hero-section" /> }));
vi.mock('../QuickLinksSection', () => ({ QuickLinksSection: () => <div data-testid="quick-links-section" /> }));
vi.mock('../MarketingBannersSection', () => ({ MarketingBannersSection: () => <div data-testid="marketing-banners-section" /> }));
vi.mock('../CategoriesSection', () => ({ CategoriesSection: () => <div data-testid="categories-section" /> }));
vi.mock('../HitsSection', () => ({ HitsSection: () => <div data-testid="hits-section" /> }));
vi.mock('../NewArrivalsSection', () => ({ NewArrivalsSection: () => <div data-testid="new-arrivals-section" /> }));
vi.mock('../PromoSection', () => ({ PromoSection: () => <div data-testid="promo-section" /> }));
vi.mock('../SaleSection', () => ({ SaleSection: () => <div data-testid="sale-section" /> }));
vi.mock('../NewsSection', () => ({ NewsSection: () => <div data-testid="news-section" /> }));
vi.mock('../BlogSection', () => ({ BlogSection: () => <div data-testid="blog-section" /> }));
vi.mock('../SubscribeNewsSection', () => ({ SubscribeNewsSection: () => <div data-testid="subscribe-section" /> }));
vi.mock('../WhyFreesportSection', () => ({ WhyFreesportSection: () => <div data-testid="why-section" /> }));
vi.mock('../DeliveryTeaser', () => ({ DeliveryTeaser: () => <div data-testid="delivery-section" /> }));
vi.mock('../AboutTeaser', () => ({ AboutTeaser: () => <div data-testid="about-section" /> }));

describe('HomePage', () => {
  it('AC1: MarketingBannersSection рендерится между QuickLinksSection и CategoriesSection', () => {
    const { container } = render(<HomePage />);

    const sections = container.querySelectorAll('[data-testid]');
    const testIds = Array.from(sections).map(el => el.getAttribute('data-testid'));

    const quickLinksIdx = testIds.indexOf('quick-links-section');
    const marketingIdx = testIds.indexOf('marketing-banners-section');
    const categoriesIdx = testIds.indexOf('categories-section');

    expect(quickLinksIdx).toBeGreaterThan(-1);
    expect(marketingIdx).toBeGreaterThan(-1);
    expect(categoriesIdx).toBeGreaterThan(-1);

    expect(marketingIdx).toBe(quickLinksIdx + 1);
    expect(categoriesIdx).toBe(marketingIdx + 1);
  });

  it('рендерит все секции главной страницы', () => {
    const { container } = render(<HomePage />);

    const expectedSections = [
      'hero-section',
      'quick-links-section',
      'marketing-banners-section',
      'categories-section',
      'hits-section',
      'new-arrivals-section',
      'promo-section',
      'sale-section',
      'news-section',
      'blog-section',
      'subscribe-section',
      'why-section',
      'delivery-section',
      'about-section',
    ];

    for (const testId of expectedSections) {
      expect(container.querySelector(`[data-testid="${testId}"]`)).toBeInTheDocument();
    }
  });
});
