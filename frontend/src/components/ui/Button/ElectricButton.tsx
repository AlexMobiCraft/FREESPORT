'use client';

import React from 'react';
import { cn } from '@/utils/cn';

interface ElectricButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
}

export function ElectricButton({
  variant = 'primary',
  size = 'md',
  className,
  children,
  style,
  ...props
}: ElectricButtonProps) {
  const sizeClasses = {
    sm: 'h-9 px-4 text-sm',
    md: 'h-11 px-6 text-base',
    lg: 'h-14 px-8 text-lg',
  };

  const variantClasses = {
    primary:
      'bg-[var(--color-primary)] text-black hover:bg-[var(--color-text-primary)] hover:text-[var(--color-primary-active)] hover:shadow-[var(--shadow-hover)] border-transparent',
    outline:
      'bg-transparent border-2 border-[var(--foreground)] text-[var(--foreground)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)]',
    ghost:
      'bg-transparent text-[var(--foreground)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-subtle)] border-transparent',
  };

  return (
    <button
      className={cn(
        'font-roboto-condensed font-semibold uppercase transition-all duration-300 flex items-center justify-center',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
      style={{
        transform: 'skewX(-12deg)',
        ...style,
      }}
      {...props}
    >
      <span style={{ transform: 'skewX(12deg)', display: 'inline-block' }}>{children}</span>
    </button>
  );
}
