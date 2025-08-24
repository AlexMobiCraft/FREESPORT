# Мультистадийная сборка для Next.js frontend
# Стадия 1: Установка зависимостей
FROM node:22-alpine AS deps

# Метаданные образа
LABEL maintainer="FREESPORT Dev Team"
LABEL version="1.0"
LABEL description="Next.js frontend для FREESPORT Platform"

# Проверка libc6-compat для совместимости
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Копирование файлов зависимостей
COPY package.json package-lock.json* ./

# Установка зависимостей
RUN npm ci --only=production --ignore-scripts --prefer-offline

# Стадия 2: Сборка приложения
FROM node:22-alpine AS builder

WORKDIR /app

# Копирование зависимостей из предыдущей стадии
COPY --from=deps /app/node_modules ./node_modules

# Копирование исходного кода
COPY . .

# Создание .env.local для сборки
ARG NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
ARG NODE_ENV=production

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=$NODE_ENV
ENV NEXT_TELEMETRY_DISABLED=1

# Сборка Next.js приложения
RUN npm run build

# Стадия 3: Production образ
FROM node:22-alpine AS runner

WORKDIR /app

# Создание пользователя приложения (не root)
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Копирование публичных файлов
COPY --from=builder /app/public ./public

# Создание директории .next с правильными разрешениями
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Копирование собранного приложения
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Переключение на пользователя приложения
USER nextjs

# Открытие порта для Next.js
EXPOSE 3000

# Установка переменных окружения
ENV PORT=3000
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Проверка работоспособности
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Запуск приложения
CMD ["node", "server.js"]