/**
 * Electric Subscribe Form Component
 * Форма подписки на email-рассылку в стиле Electric Orange
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import { subscribeService } from '@/services/subscribeService';
import { ElectricButton } from '@/components/ui/Button/ElectricButton';
import { cn } from '@/utils/cn';

interface SubscribeFormData {
  email: string;
  pdp_consent: boolean;
}

export const ElectricSubscribeForm: React.FC = () => {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<SubscribeFormData>({
    defaultValues: { email: '', pdp_consent: false },
  });

  const pdpConsent = watch('pdp_consent');
  const pdpConsentRegistration = register('pdp_consent', {
    required: 'Необходимо согласие на обработку персональных данных',
  });
  const hasPdpConsentError = !!errors.pdp_consent;

  const onSubmit = async (data: SubscribeFormData) => {
    try {
      await subscribeService.subscribe({
        email: data.email,
        pdp_consent: data.pdp_consent,
      });
      toast.success('ВЫ УСПЕШНО ПОДПИСАЛИСЬ НА РАССЫЛКУ!', {
        style: {
          borderRadius: '0',
          background: '#000',
          color: '#fff',
          border: '1px solid #FF6600',
        },
      });
      reset();
    } catch (error: unknown) {
      // Error handling similar to original but with toast styles if we want
      if (error instanceof Error && error.message === 'already_subscribed') {
        toast.error('ЭТОТ EMAIL УЖЕ ПОДПИСАН', {
          style: { borderRadius: '0', background: '#000', color: '#fff', border: '1px solid red' },
        });
      } else {
        toast.error('ОШИБКА ПОДПИСКИ', {
          style: { borderRadius: '0', background: '#000', color: '#fff', border: '1px solid red' },
        });
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-6 max-w-xl mx-auto md:max-w-none md:mx-0"
    >
      <div>
        <h3 className="text-2xl md:text-3xl font-bold text-[var(--foreground)] uppercase mb-2 transform -skew-x-12">
          <span className="inline-block transform skew-x-12">Подписаться на рассылку</span>
        </h3>
        <p className="text-[var(--color-text-secondary)] font-inter text-sm md:text-base">
          Получайте первыми информацию о новинках и акциях
        </p>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="email-subscribe"
          className="block text-sm font-bold text-[var(--foreground)] uppercase transform -skew-x-12"
        >
          <span className="inline-block transform skew-x-12">Email</span>
        </label>
        <div className="relative transform -skew-x-12">
          <input
            id="email-subscribe"
            type="email"
            placeholder="your@email.com"
            className={`
                   w-full bg-[var(--bg-card)] border-2 px-4 py-3 outline-none transition-all duration-300 transform skew-x-12
                   placeholder:text-[var(--color-text-muted)]
                   ${
                     errors.email
                       ? 'border-red-500 focus:border-red-500'
                       : 'border-[var(--border-default)] focus:border-[var(--color-primary)]'
                   }
                `}
            {...register('email', {
              required: 'Email обязателен',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Введите корректный email',
              },
            })}
          />
        </div>
        {errors.email && (
          <p className="text-red-500 text-xs font-bold uppercase mt-1">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <div className="flex items-start gap-3">
          <div className="relative flex items-center pt-0.5">
            <input
              id="electric-subscribe-pdp-consent"
              type="checkbox"
              className="sr-only peer"
              disabled={isSubmitting}
              name={pdpConsentRegistration.name}
              ref={pdpConsentRegistration.ref}
              onBlur={pdpConsentRegistration.onBlur}
              checked={pdpConsent}
              onChange={event => {
                void pdpConsentRegistration.onChange(event);
                setValue('pdp_consent', event.target.checked, { shouldValidate: true });
              }}
              aria-invalid={hasPdpConsentError || undefined}
              aria-labelledby="electric-subscribe-pdp-consent-label-prefix electric-subscribe-pdp-consent-policy-link electric-subscribe-pdp-consent-label-suffix"
              aria-describedby={
                hasPdpConsentError ? 'electric-subscribe-pdp-consent-error' : undefined
              }
            />
            <label
              htmlFor="electric-subscribe-pdp-consent"
              className={cn(
                'flex h-5 w-5 cursor-pointer items-center justify-center border-2 transition-all duration-150',
                'transform -skew-x-12',
                'peer-checked:border-[var(--color-primary)] peer-checked:bg-[var(--color-primary)]',
                'peer-focus:ring-2 peer-focus:ring-[var(--color-primary)]/30 peer-focus:ring-offset-2',
                hasPdpConsentError
                  ? 'border-red-500 peer-focus:ring-red-500/30'
                  : 'border-[var(--color-primary)] hover:bg-[var(--color-primary)]/15',
                isSubmitting && 'cursor-not-allowed opacity-50'
              )}
            >
              {pdpConsent && (
                <span className="transform skew-x-12 text-xs font-bold text-black">✓</span>
              )}
            </label>
          </div>
          <span className="font-inter text-xs md:text-sm uppercase leading-relaxed text-[var(--color-text-secondary)]">
            <label
              id="electric-subscribe-pdp-consent-label-prefix"
              htmlFor="electric-subscribe-pdp-consent"
              className="cursor-pointer"
            >
              Я даю согласие на
            </label>{' '}
            <Link
              id="electric-subscribe-pdp-consent-policy-link"
              href="/privacy-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-primary)] underline hover:text-[var(--foreground)]"
            >
              обработку моих персональных данных
            </Link>{' '}
            <label
              id="electric-subscribe-pdp-consent-label-suffix"
              htmlFor="electric-subscribe-pdp-consent"
              className="cursor-pointer"
            >
              в соответствии с Политикой
            </label>
          </span>
        </div>
        {errors.pdp_consent?.message && (
          <p
            id="electric-subscribe-pdp-consent-error"
            className="text-red-500 text-xs font-bold uppercase mt-1"
            role="alert"
          >
            {errors.pdp_consent.message}
          </p>
        )}
      </div>

      <ElectricButton
        type="submit"
        variant="primary"
        size="lg"
        disabled={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? 'ОТПРАВКА...' : 'ПОДПИСАТЬСЯ'}
      </ElectricButton>
    </form>
  );
};
