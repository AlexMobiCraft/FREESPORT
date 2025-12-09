/**
 * Axios API Client - централизованная конфигурация для всех API запросов
 *
 * Features:
 * - Автоматическое добавление JWT токенов
 * - Refresh token flow с очередью concurrent requests
 * - Retry logic для network/server errors
 * - Exponential backoff
 */

import axios, {
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
  AxiosResponse,
} from 'axios';
import { useAuthStore } from '@/stores/authStore';

// Конфигурация из environment variables
// Для SSR используем внутренний URL (внутри Docker сети), для браузера - публичный
// INTERNAL_API_URL - серверная переменная (без NEXT_PUBLIC_ префикса), доступна в runtime
// NEXT_PUBLIC_API_URL - клиентская переменная, встраивается при сборке
const isServer = typeof window === 'undefined';
const API_URL_PUBLIC = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
const API_URL_INTERNAL =
  process.env.INTERNAL_API_URL
    ? `${process.env.INTERNAL_API_URL}/api/v1`
    : process.env.NEXT_PUBLIC_API_URL_INTERNAL || 'http://backend:8000/api/v1';
const API_URL = isServer ? API_URL_INTERNAL : API_URL_PUBLIC;
const API_TIMEOUT = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '30000');

// Create axios instance
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
  // ВАЖНО: withCredentials включает отправку cookies (sessionid) для гостевых корзин
  withCredentials: true,
});

// State для refresh token handling (предотвращение race conditions)
let isRefreshing = false;
let failedQueue: Array<{ resolve: (value?: unknown) => void; reject: (reason?: unknown) => void }> =
  [];

/**
 * Обрабатывает очередь запросов после refresh token
 */
const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Retry helper с exponential backoff
 */
const retryRequest = async (config: AxiosRequestConfig, retryCount = 0): Promise<AxiosResponse> => {
  try {
    // Ensure baseURL is preserved for retry requests (fixes ECONNREFUSED in Docker SSR)
    const retryConfig: AxiosRequestConfig = {
      ...config,
      baseURL: config.baseURL || API_URL,
    };
    return await axios(retryConfig);
  } catch (error) {
    const axiosError = error as AxiosError;
    const shouldRetry =
      retryCount < 3 &&
      (axiosError.code === 'ECONNREFUSED' ||
        axiosError.code === 'ETIMEDOUT' ||
        axiosError.code === 'ENOTFOUND' ||
        axiosError.response?.status === 500 ||
        axiosError.response?.status === 503);

    if (shouldRetry) {
      const delay = Math.pow(2, retryCount) * 1000; // 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, delay));
      return retryRequest(config, retryCount + 1);
    }

    throw error;
  }
};

/**
 * Request interceptor - добавляет JWT token в Authorization header
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().accessToken;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

/**
 * Response interceptor - обработка 401 ошибки с refresh token flow
 */
apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // Если refresh уже в процессе - добавить в очередь
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(token => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = useAuthStore.getState().getRefreshToken();

      if (!refreshToken) {
        // No refresh token - logout
        useAuthStore.getState().logout();
        processQueue(error, null);
        isRefreshing = false;
        return Promise.reject(error);
      }

      try {
        // Call refresh endpoint
        const response = await axios.post<{ access: string }>(`${API_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;

        // Update access token in store
        useAuthStore.getState().setTokens(access, refreshToken);

        // Process queued requests
        processQueue(null, access);

        // Retry original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access}`;
        }
        isRefreshing = false;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - logout
        processQueue(refreshError, null);
        useAuthStore.getState().logout();
        isRefreshing = false;
        return Promise.reject(refreshError);
      }
    }

    // Retry logic для network errors и server errors
    const shouldRetry =
      error.code === 'ECONNREFUSED' ||
      error.code === 'ETIMEDOUT' ||
      error.code === 'ENOTFOUND' ||
      error.response?.status === 500 ||
      error.response?.status === 503;

    if (shouldRetry && originalRequest && !originalRequest._retry) {
      return retryRequest(originalRequest);
    }

    return Promise.reject(error);
  }
);

export default apiClient;
