import path from 'path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Настройки для Docker deployment
  // output: 'standalone', // Отключаем standalone режим

  // Experimental features
  experimental: {
    // Убрана оптимизация CSS из-за ошибки с critters
  },

  // Настройки Turbopack (теперь стабильная функция)
  turbopack: {
    rules: {
      '*.svg': ['@svgr/webpack'],
    },
  },

  // Настройки изображений
  images: {
    domains: [
      'localhost',
      // TODO: Добавить домены для продакшена
    ],
    formats: ['image/webp', 'image/avif'],
  },

  // Переписывание URL для API прокси в разработке
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/:path*`
          : 'http://localhost:8001/api/v1/:path*',
      },
    ];
  },

  // Заголовки безопасности
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Настройки компиляции
  compiler: {
    // Удаление console.log в продакшене
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Оптимизация бандла
  webpack: (config, { dev, isServer }) => {
    // Оптимизации для клиентской стороны
    if (!dev && !isServer) {
      config.resolve.alias = {
        ...config.resolve.alias,
        '@/components': path.resolve(__dirname, 'src/components'),
        '@/hooks': path.resolve(__dirname, 'src/hooks'),
        '@/services': path.resolve(__dirname, 'src/services'),
        '@/stores': path.resolve(__dirname, 'src/stores'),
        '@/types': path.resolve(__dirname, 'src/types'),
        '@/utils': path.resolve(__dirname, 'src/utils'),
      };
    }

    return config;
  },

  // Переменные окружения для клиента
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // Настройки TypeScript
  typescript: {
    // Не останавливать сборку при ошибках TypeScript в разработке
    ignoreBuildErrors: false,
  },

  // ESLint настройки
  eslint: {
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;
