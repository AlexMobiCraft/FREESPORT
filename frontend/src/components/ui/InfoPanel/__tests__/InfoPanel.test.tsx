/**
 * InfoPanel Component Tests
 * Покрытие dismissible, длинного текста, иконок
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { InfoPanel } from '../InfoPanel';

describe('InfoPanel', () => {
  // Базовый рендеринг
  it('renders info panel with text', () => {
    render(<InfoPanel>Important information</InfoPanel>);

    expect(screen.getByText('Important information')).toBeInTheDocument();
  });

  // Icon
  describe('Icon', () => {
    it('renders default Info icon when not provided', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const icon = container.querySelector('svg[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });

    it('renders custom icon when provided', () => {
      const CustomIcon = () => <svg data-testid="custom-icon" />;
      render(<InfoPanel icon={<CustomIcon />}>Message</InfoPanel>);

      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });

    it('icon has proper styling', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const iconContainer = container.querySelector('.w-20.h-20');
      expect(iconContainer).toHaveClass('rounded-xl', 'bg-[#00B7FF]/16');
    });
  });

  // Edge Case: Dismissible
  describe('Dismissible', () => {
    it('does not show close button when onDismiss is not provided', () => {
      render(<InfoPanel>Message</InfoPanel>);

      const closeButton = screen.queryByLabelText('Закрыть');
      expect(closeButton).not.toBeInTheDocument();
    });

    it('shows close button when onDismiss is provided', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      expect(closeButton).toBeInTheDocument();
    });

    it('calls onDismiss when close button is clicked', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      fireEvent.click(closeButton);

      expect(handleDismiss).toHaveBeenCalledTimes(1);
    });

    it('hides panel when close button is clicked', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      fireEvent.click(closeButton);

      expect(screen.queryByText('Message')).not.toBeInTheDocument();
    });

    it('close button has hover effect', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      expect(closeButton).toHaveClass('hover:bg-neutral-200');
    });

    it('close button has focus ring', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      expect(closeButton).toHaveClass('focus:ring-2', 'focus:ring-primary');
    });
  });

  // Edge Case: Длинный текст
  describe('Long Text', () => {
    it('wraps long text to multiple lines', () => {
      const longText =
        'This is a very long informational message that should wrap to multiple lines and not overflow the container. It should be readable and properly formatted.';
      const { container } = render(<InfoPanel>{longText}</InfoPanel>);

      const textContainer = container.querySelector('.whitespace-normal');
      expect(textContainer).toHaveClass('break-words');
    });

    it('has proper text styling', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const textContainer = container.querySelector('.text-body-m');
      expect(textContainer).toHaveClass('text-text-primary');
    });
  });

  // Edge Case: Fade-out анимация
  describe('Fade-out Animation', () => {
    it('has transition duration of 200ms', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const panel = container.firstChild as HTMLElement;
      expect(panel).toHaveClass('transition-opacity', 'duration-[200ms]');
    });
  });

  // Styling
  describe('Styling', () => {
    it('has grid layout', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const panel = container.firstChild as HTMLElement;
      expect(panel).toHaveClass('grid', 'grid-cols-[auto_1fr]', 'gap-4');
    });

    it('has proper background and border', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const panel = container.firstChild as HTMLElement;
      expect(panel).toHaveClass('bg-neutral-100', 'border-primary/20');
    });

    it('has rounded corners', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const panel = container.firstChild as HTMLElement;
      expect(panel).toHaveClass('rounded-md');
    });

    it('has proper padding', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const panel = container.firstChild as HTMLElement;
      expect(panel).toHaveClass('p-5');
    });
  });

  // Accessibility
  describe('Accessibility', () => {
    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<InfoPanel ref={ref}>Message</InfoPanel>);

      expect(ref.current).toBeInstanceOf(HTMLDivElement);
    });

    it('close button has aria-label', () => {
      const handleDismiss = vi.fn();
      render(<InfoPanel onDismiss={handleDismiss}>Message</InfoPanel>);

      const closeButton = screen.getByLabelText('Закрыть');
      expect(closeButton).toHaveAttribute('aria-label', 'Закрыть');
    });

    it('icon has aria-hidden', () => {
      const { container } = render(<InfoPanel>Message</InfoPanel>);

      const icon = container.querySelector('svg');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });

  // Custom className
  it('accepts custom className', () => {
    const { container } = render(<InfoPanel className="custom-class">Message</InfoPanel>);

    const panel = container.firstChild as HTMLElement;
    expect(panel).toHaveClass('custom-class');
  });

  // Custom props
  it('accepts custom HTML attributes', () => {
    render(<InfoPanel data-testid="custom-panel">Message</InfoPanel>);

    expect(screen.getByTestId('custom-panel')).toBeInTheDocument();
  });

  // Complex content
  it('renders complex nested content', () => {
    render(
      <InfoPanel>
        <div>
          <strong>Important:</strong> This is a message with <em>formatting</em>.
        </div>
      </InfoPanel>
    );

    expect(screen.getByText(/Important:/)).toBeInTheDocument();
    expect(screen.getByText(/formatting/)).toBeInTheDocument();
  });
});
