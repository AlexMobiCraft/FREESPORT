'use client';

import { useCookieConsent } from '@/hooks/useCookieConsent';

export interface CookieSettingsButtonProps {
  /** Классы подвала: палитру задаёт вызывающая сторона, а не сама кнопка. */
  className?: string;
}

/**
 * Кнопка «Настройки cookie» для подвала (Story 41.1, FR-41-02).
 *
 * Один компонент на все три подвала (`Footer`, `ElectricFooter` и собственный
 * подвал `/coming-soon`). Рендерится ВСЕГДА, независимо от сохранённого
 * выбора: условный рендер по состоянию согласия даёт расхождение серверной и
 * клиентской разметки.
 */
export default function CookieSettingsButton({ className }: CookieSettingsButtonProps) {
  const { reopen } = useCookieConsent();

  return (
    <button type="button" onClick={reopen} className={className}>
      Настройки cookie
    </button>
  );
}
