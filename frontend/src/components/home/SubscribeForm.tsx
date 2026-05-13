/**
 * SubscribeForm Component
 * Форма подписки на email-рассылку
 *
 * @see Story 11.3 - AC 1, 2, 5
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import { subscribeService } from '@/services/subscribeService';
import { Input } from '@/components/ui/Input/Input';
import { Button } from '@/components/ui/Button/Button';
import { Checkbox } from '@/components/ui/Checkbox/Checkbox';

interface SubscribeFormData {
  email: string;
  pdp_consent: boolean;
}

export const SubscribeForm: React.FC = () => {
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
      toast.success('Вы успешно подписались на рассылку');
      reset();
    } catch (error: unknown) {
      if (error instanceof Error) {
        if (error.message === 'already_subscribed') {
          toast.error('Этот email уже подписан на рассылку');
        } else if (error.message === 'validation_error') {
          toast.error('Введите корректный email');
        } else {
          toast.error('Не удалось подписаться. Попробуйте позже');
        }
      } else {
        toast.error('Не удалось подписаться. Попробуйте позже');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <h3 className="text-xl font-semibold text-text-primary">Подписаться на рассылку</h3>
      <p className="text-sm text-text-secondary">
        Получайте первыми информацию о новинках и акциях
      </p>
      <Input
        label="Электронная почта"
        type="email"
        placeholder="your@email.com"
        error={errors.email?.message}
        aria-required="true"
        aria-invalid={!!errors.email}
        {...register('email', {
          required: 'Email обязателен',
          pattern: {
            value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
            message: 'Введите корректный email',
          },
        })}
      />
      <div className="space-y-2">
        <div className="flex items-start gap-3">
          <Checkbox
            id="subscribe-pdp-consent"
            name={pdpConsentRegistration.name}
            ref={pdpConsentRegistration.ref}
            onBlur={pdpConsentRegistration.onBlur}
            onChange={event => {
              void pdpConsentRegistration.onChange(event);
              setValue('pdp_consent', event.target.checked, { shouldValidate: true });
            }}
            checked={pdpConsent}
            disabled={isSubmitting}
            aria-invalid={hasPdpConsentError || undefined}
            aria-labelledby="subscribe-pdp-consent-label-prefix subscribe-pdp-consent-policy-link subscribe-pdp-consent-label-suffix"
            aria-describedby={hasPdpConsentError ? 'subscribe-pdp-consent-error' : undefined}
            className={
              hasPdpConsentError
                ? 'border-[var(--color-accent-danger)] bg-[var(--color-accent-danger)]/8 peer-focus:ring-[var(--color-accent-danger)]'
                : undefined
            }
          />
          <span className="text-body-s text-text-primary select-none">
            <label
              id="subscribe-pdp-consent-label-prefix"
              htmlFor="subscribe-pdp-consent"
              className="cursor-pointer"
            >
              Я даю согласие на
            </label>{' '}
            <Link
              id="subscribe-pdp-consent-policy-link"
              href="/privacy-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline hover:text-primary-hover"
            >
              обработку моих персональных данных
            </Link>{' '}
            <label
              id="subscribe-pdp-consent-label-suffix"
              htmlFor="subscribe-pdp-consent"
              className="cursor-pointer"
            >
              в соответствии с Политикой
            </label>
          </span>
        </div>
        {errors.pdp_consent?.message && (
          <p
            id="subscribe-pdp-consent-error"
            className="text-body-xs text-[var(--color-accent-danger)]"
            role="alert"
          >
            {errors.pdp_consent.message}
          </p>
        )}
      </div>
      <Button
        type="submit"
        variant="primary"
        disabled={isSubmitting}
        loading={isSubmitting}
        className="w-full"
      >
        {isSubmitting ? 'Отправка...' : 'Подписаться'}
      </Button>
    </form>
  );
};
