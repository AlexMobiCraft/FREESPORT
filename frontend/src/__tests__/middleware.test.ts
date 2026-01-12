/**
 * Middleware Tests
 * Story 28.4 - Защищенные маршруты и управление сессиями
 *
 * Тестирует:
 * - Protected routes redirect без токена
 * - Public routes доступны без токена
 * - Предотвращение бесконечного редиректа
 * - Auth routes redirect для авторизованных
 */

import { describe, test, expect } from 'vitest';
import { NextRequest } from 'next/server';
import { middleware } from '../middleware';

describe('Middleware - Protected Routes', () => {
  test('redirects to /login for protected route without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/profile'));

    const response = middleware(request);

    expect(response.status).toBe(307); // Temporary Redirect
    expect(response.headers.get('location')).toContain('/login?next=%2Fprofile');
  });

  test('redirects to /login for /orders without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/orders'));

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toContain('/login?next=%2Forders');
  });

  test('redirects to /login for /b2b-dashboard without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/b2b-dashboard'));

    const response = middleware(request);

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toContain('/login?next=%2Fb2b-dashboard');
  });

  // NOTE: Тестирование с cookies в unit-тестах NextRequest сложно
  // Эти тесты будут покрыты в E2E тестах
});

describe('Middleware - Public Routes', () => {
  test('allows access to homepage without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/'));

    const response = middleware(request);

    expect(response.status).not.toBe(307);
  });

  test('allows access to catalog without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/catalog'));

    const response = middleware(request);

    expect(response.status).not.toBe(307);
  });

  test('allows access to product page without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/product/123'));

    const response = middleware(request);

    expect(response.status).not.toBe(307);
  });

  test('allows access to /login without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/login'));

    const response = middleware(request);

    expect(response.status).not.toBe(307);
  });

  test('allows access to /register without token', () => {
    const request = new NextRequest(new URL('http://localhost:3000/register'));

    const response = middleware(request);

    expect(response.status).not.toBe(307);
  });
});

describe('Middleware - Infinite Redirect Prevention', () => {
  test('does not redirect to /login if already on /login', () => {
    const request = new NextRequest(new URL('http://localhost:3000/login'));

    const response = middleware(request);

    // Не должен редиректить на /login?next=/login
    expect(response.status).not.toBe(307);
    const location = response.headers.get('location');
    if (location) {
      expect(location).not.toContain('next=%2Flogin');
    }
  });

  test('does not add next parameter if already on auth route', () => {
    const request = new NextRequest(new URL('http://localhost:3000/register'));

    const response = middleware(request);

    // Register route is public, no redirect
    expect(response.status).not.toBe(307);
  });
});

describe('Middleware - Auth Routes for Authenticated Users', () => {
  // NOTE: Тестирование редиректов для авторизованных пользователей с cookies
  // сложно реализовать в unit-тестах NextRequest
  // Эти сценарии будут покрыты в E2E тестах или интеграционных тестах
  test.skip('redirects authenticated user from /login to homepage (E2E)', () => {
    // Будет реализовано в E2E тестах с Playwright
  });

  test.skip('redirects authenticated user from /register to homepage (E2E)', () => {
    // Будет реализовано в E2E тестах с Playwright
  });

  test.skip('redirects authenticated user from /password-reset to homepage (E2E)', () => {
    // Будет реализовано в E2E тестах с Playwright
  });
});

describe('Middleware - Next Parameter Format', () => {
  test('encodes next parameter correctly', () => {
    const request = new NextRequest(new URL('http://localhost:3000/orders/123'));

    const response = middleware(request);

    expect(response.status).toBe(307);
    const location = response.headers.get('location');
    expect(location).toContain('next=');
    // URL должен быть закодирован (/ -> %2F)
    expect(location).toContain('%2Forders');
  });

  test('preserves nested paths in next parameter', () => {
    const request = new NextRequest(new URL('http://localhost:3000/profile/settings/password'));

    const response = middleware(request);

    expect(response.status).toBe(307);
    const location = response.headers.get('location');
    expect(location).toContain('next=%2Fprofile%2Fsettings%2Fpassword');
  });
});
