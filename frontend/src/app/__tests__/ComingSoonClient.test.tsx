/**
 * Регрессионные тесты страницы /coming-soon.
 * Story 41.3 — AC5 (FR-41-04): формы подписки на странице быть не должно.
 *
 * Форма собирала email без правового основания, без согласия и без ссылки
 * на политику, а адрес никуда не сохранялся. Она удалена; этот файл
 * существует, чтобы её возврат падал в CI, а не проходил незамеченным.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ComingSoon from '../ComingSoonClient';

// Мок motion/react: анимации в тестах не нужны, важна только разметка
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => (
      <div {...filterMotionProps(props)}>{children}</div>
    ),
  },
}));

// Отбрасывает специфичные для motion пропсы, невалидные как HTML-атрибуты
function filterMotionProps(props: Record<string, unknown>) {
  const htmlProps: Record<string, unknown> = {};
  const motionKeys = ['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover'];
  for (const [key, value] of Object.entries(props)) {
    if (!motionKeys.includes(key)) {
      htmlProps[key] = value;
    }
  }
  return htmlProps;
}

describe('ComingSoonClient — AC5: формы подписки нет', () => {
  it('не содержит ни одного поля ввода', () => {
    const { container } = render(<ComingSoon />);

    expect(container.querySelectorAll('input')).toHaveLength(0);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('не содержит формы и кнопки подписки', () => {
    const { container } = render(<ComingSoon />);

    expect(container.querySelectorAll('form')).toHaveLength(0);
    expect(container.querySelectorAll('button')).toHaveLength(0);
    expect(screen.queryByRole('button', { name: /подписаться/i })).not.toBeInTheDocument();
  });

  it('не обещает уведомление о запуске', () => {
    render(<ComingSoon />);

    expect(screen.queryByText(/узнайте первым о нашем запуске/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/уведомим вас о запуске/i)).not.toBeInTheDocument();
  });

  it('сохраняет канал связи в подвале', () => {
    render(<ComingSoon />);

    expect(screen.getByText(/info@optisport\.ru/)).toBeInTheDocument();
  });

  it('оставляет содержательную часть страницы нетронутой', () => {
    render(<ComingSoon />);

    expect(screen.getByRole('heading', { name: /мы скоро вернемся/i })).toBeInTheDocument();
    expect(screen.getByText(/разработка идет по плану/i)).toBeInTheDocument();
  });
});
