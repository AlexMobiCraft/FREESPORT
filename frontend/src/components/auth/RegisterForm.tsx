/**
 * RegisterForm Component
 * Story 28.1 - Базовая аутентификация и регистрация B2C
 *
 * Форма регистрации B2C пользователей с валидацией
 *
 * AC 2: B2C Registration Flow с автологином
 * AC 3: Client-side валидация (Zod)
 * AC 4: Error Handling и Loading States
 * AC 5: Интеграция с authService
 * AC 6: Использование UI компонентов
 * AC 7: Responsive Design
 * AC 10: Accessibility
 */

'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { Input } from '@/components/ui/Input/Input';
import { Button } from '@/components/ui/Button/Button';
import authService from '@/services/authService';
import { registerSchema, type RegisterFormData } from '@/schemas/authSchemas';
import type { RegisterRequest } from '@/types/api';

export interface RegisterFormProps {
  /** Callback после успешной регистрации (optional) */
  onSuccess?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    try {
      setApiError(null);

      // AC 5: Используем authService.register()
      // Note: confirmPassword не отправляется на backend (только клиентская валидация)
      const registerData: RegisterRequest = {
        email: data.email,
        password: data.password,
        password_confirm: data.confirmPassword,
        first_name: data.first_name,
        last_name: '', // B2C registration может не требовать фамилию
        phone: '', // B2C может не требовать телефон при регистрации
        role: 'retail', // По умолчанию для B2C
      };

      // AC 2: Автоматический вход после регистрации
      await authService.register(registerData);

      // Callback при успехе
      if (onSuccess) {
        onSuccess();
      }

      // AC 2: Редирект на главную после успешной регистрации
      router.push('/test');
    } catch (error: unknown) {
      // AC 4: Обработка ошибок API
      const err = error as {
        response?: {
          status?: number;
          data?: Record<string, string[] | string>;
        };
      };
      if (err.response?.status === 409) {
        // Конфликт - пользователь уже существует
        const emailError = err.response?.data?.email?.[0];
        setApiError(emailError || 'Пользователь с таким email уже существует');
      } else if (err.response?.status === 400) {
        // Ошибки валидации
        const data = err.response?.data || {};
        // Ищем первую ошибку в ответе
        const firstErrorKey = Object.keys(data).find(key => key !== 'detail');
        const firstError = firstErrorKey ? data[firstErrorKey] : null;
        const errorMessage = Array.isArray(firstError) ? firstError[0] : firstError;

        setApiError(errorMessage || 'Ошибка валидации данных');
      } else if (err.response?.status === 500) {
        setApiError('Ошибка сервера. Попробуйте позже');
      } else {
        setApiError((err.response?.data?.detail as string) || 'Произошла ошибка при регистрации');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-md mx-auto p-6 space-y-4">
      {/* AC 4: Отображение API ошибок */}
      {apiError && (
        <div
          className="p-4 rounded-md bg-[var(--color-accent-danger)]/10 border border-[var(--color-accent-danger)]"
          role="alert"
          aria-live="assertive"
        >
          <p className="text-body-s text-[var(--color-accent-danger)]">{apiError}</p>
        </div>
      )}

      {/* AC 6: Использование Input компонента */}
      {/* AC 10: Label с htmlFor, aria-describedby */}
      <Input
        label="Имя"
        type="text"
        {...register('first_name')}
        error={errors.first_name?.message}
        disabled={isSubmitting}
        autoComplete="given-name"
        placeholder="Иван"
      />

      <Input
        label="Email"
        type="email"
        {...register('email')}
        error={errors.email?.message}
        disabled={isSubmitting}
        autoComplete="email"
        placeholder="user@example.com"
      />

      <Input
        label="Пароль"
        type="password"
        {...register('password')}
        error={errors.password?.message}
        disabled={isSubmitting}
        autoComplete="new-password"
        placeholder="••••••••"
        helper="Минимум 8 символов, 1 цифра и 1 заглавная буква"
      />

      <Input
        label="Подтверждение пароля"
        type="password"
        {...register('confirmPassword')}
        error={errors.confirmPassword?.message}
        disabled={isSubmitting}
        autoComplete="new-password"
        placeholder="••••••••"
      />

      {/* AC 6: Использование Button компонента */}
      {/* AC 4: Loading state с блокировкой кнопки */}
      <Button type="submit" loading={isSubmitting} disabled={isSubmitting} className="w-full">
        Зарегистрироваться
      </Button>
    </form>
  );
};
