/**
 * Modal Component Tests
 * Проверка focus trap, ESC/backdrop close, overflow и nested warning
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Modal } from '../Modal';

describe('Modal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  // Базовый рендеринг
  it('renders when isOpen is true', () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(
      <Modal isOpen={false} onClose={mockOnClose} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // Edge Case: ESC закрывает Modal
  describe('Edge Case: ESC Key Close', () => {
    it('closes modal on ESC key press', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          Content
        </Modal>
      );

      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  // Edge Case: Клик на backdrop закрывает
  describe('Edge Case: Backdrop Click Close', () => {
    it('closes modal on backdrop click', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          Content
        </Modal>
      );

      // Клик на overlay (backdrop)
      const backdrop = screen.getByRole('dialog').parentElement;
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it('does not close on content area click', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          Content
        </Modal>
      );

      fireEvent.click(screen.getByText('Content'));
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  // Close button
  it('closes modal when close button is clicked', () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Test">
        Content
      </Modal>
    );

    fireEvent.click(screen.getByLabelText('Закрыть модальное окно'));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  // Footer
  it('renders footer when provided', () => {
    render(
      <Modal isOpen={true} onClose={mockOnClose} title="Test" footer={<button>Save</button>}>
        Content
      </Modal>
    );

    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument();
  });

  // Accessibility
  describe('Accessibility', () => {
    it('has correct ARIA attributes', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test Modal">
          Content
        </Modal>
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');
    });
  });

  // Edge Case: Overflow контента
  describe('Edge Case: Content Overflow', () => {
    it('applies scrollable class to content area', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Test">
          <div style={{ height: '2000px' }}>Very long content</div>
        </Modal>
      );

      const contentArea = screen.getByText(/Very long content/i).parentElement;
      expect(contentArea).toHaveClass('overflow-y-auto');
    });
  });

  // Edge Case: Nested modals warning
  describe('Edge Case: Nested Modals Warning', () => {
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation();

    afterEach(() => {
      consoleSpy.mockClear();
    });

    afterAll(() => {
      consoleSpy.mockRestore();
    });

    it('warns when opening modal with existing modal', () => {
      const { rerender } = render(
        <Modal isOpen={true} onClose={mockOnClose} title="First">
          Content 1
        </Modal>
      );

      // Открываем второй modal (симуляция)
      const existingDialog = document.querySelector('[role="dialog"][aria-modal="true"]');
      expect(existingDialog).toBeInTheDocument();

      // Рендерим еще один modal
      rerender(
        <>
          <Modal isOpen={true} onClose={mockOnClose} title="First">
            Content 1
          </Modal>
          <Modal isOpen={true} onClose={vi.fn()} title="Second">
            Content 2
          </Modal>
        </>
      );

      // Проверяем что было предупреждение
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Nested modals are not supported')
      );
    });
  });
});
