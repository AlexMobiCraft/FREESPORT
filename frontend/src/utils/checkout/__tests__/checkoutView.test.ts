import { describe, expect, it } from 'vitest';
import { resolveCheckoutView, type CheckoutViewInput } from '../checkoutView';

function makeInput(overrides: Partial<CheckoutViewInput> = {}): CheckoutViewInput {
  return {
    isAuthInitialized: true,
    isAuthenticated: true,
    cartLoad: 'ready',
    hasItems: true,
    isRedirecting: false,
    ...overrides,
  };
}

describe('resolveCheckoutView', () => {
  it('возвращает loading, пока сессия не восстановлена, при любых остальных значениях', () => {
    expect(
      resolveCheckoutView(
        makeInput({
          isAuthInitialized: false,
          isAuthenticated: true,
          cartLoad: 'ready',
          hasItems: true,
          isRedirecting: true,
        })
      )
    ).toBe('loading');
    expect(
      resolveCheckoutView(
        makeInput({
          isAuthInitialized: false,
          isAuthenticated: false,
          cartLoad: 'error',
          hasItems: false,
        })
      )
    ).toBe('loading');
  });

  it('возвращает anonymous для не вошедшего пользователя, даже если в корзине есть товары', () => {
    expect(
      resolveCheckoutView(
        makeInput({ isAuthenticated: false, cartLoad: 'ready', hasItems: true })
      )
    ).toBe('anonymous');
  });

  it('возвращает loading, пока корзина авторизованного пользователя загружается', () => {
    expect(resolveCheckoutView(makeInput({ cartLoad: 'pending' }))).toBe('loading');
  });

  it('возвращает error при ошибке загрузки корзины, даже если есть товары', () => {
    expect(
      resolveCheckoutView(makeInput({ cartLoad: 'error', hasItems: true }))
    ).toBe('error');
  });

  it('возвращает redirecting при пустой корзине после оформления заказа', () => {
    expect(
      resolveCheckoutView(
        makeInput({ cartLoad: 'ready', hasItems: false, isRedirecting: true })
      )
    ).toBe('redirecting');
  });

  it('возвращает empty для готовой пустой корзины без редиректа', () => {
    expect(
      resolveCheckoutView(
        makeInput({ cartLoad: 'ready', hasItems: false, isRedirecting: false })
      )
    ).toBe('empty');
  });

  it('возвращает form для готовой корзины с товарами', () => {
    expect(
      resolveCheckoutView(
        makeInput({ cartLoad: 'ready', hasItems: true, isRedirecting: false })
      )
    ).toBe('form');
  });
});
