'use client';

/**
 * Providers Component
 * Клиентская обёртка для всех провайдеров приложения
 */

import React from 'react';
import { ToastProvider } from '@/components/ui/Toast/ToastProvider';

interface ProvidersProps {
  children: React.ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  return <ToastProvider>{children}</ToastProvider>;
}
