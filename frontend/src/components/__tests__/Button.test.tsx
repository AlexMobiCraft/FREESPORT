/**
 * Тесты компонента Button для FREESPORT Platform
 */
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Button from '@/components/ui/Button'
import '@testing-library/jest-dom'

// Импортируем типы для использования в тестах
type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

describe('Button', () => {
  // Тест базовой функциональности
  it('отображается с правильным текстом', () => {
    render(<Button>Нажми меня</Button>)
    
    expect(screen.getByRole('button', { name: 'Нажми меня' })).toBeInTheDocument()
  })

  // Тест обработки клика
  it('вызывает onClick при нажатии', async () => {
    const handleClick = jest.fn()
    const user = userEvent.setup()
    
    render(<Button onClick={handleClick}>Кнопка</Button>)
    
    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  // Параметризированные тесты для вариантов стилей
  it.each([
    ['primary', 'bg-blue-600'],
    ['secondary', 'bg-gray-600'],
    ['outline', 'border-gray-300'],
    ['ghost', 'bg-transparent'],
    ['danger', 'bg-red-600'],
  ])('применяет правильные стили для варианта %s', (variant, expectedClass) => {
    render(<Button variant={variant as ButtonVariant}>Кнопка</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass(expectedClass)
  })

  // Параметризированные тесты для размеров
  it.each([
    ['sm', 'px-3 py-2 text-sm'],
    ['md', 'px-4 py-2 text-base'],
    ['lg', 'px-6 py-3 text-lg'],
  ])('применяет правильные стили для размера %s', (size, expectedClass) => {
    render(<Button size={size as ButtonSize}>Кнопка</Button>)
    
    const button = screen.getByRole('button')
    expectedClass.split(' ').forEach(cls => {
      expect(button).toHaveClass(cls)
    })
  })

  // Тест состояния disabled
  it('корректно обрабатывает состояние disabled', () => {
    const handleClick = jest.fn()
    
    render(<Button disabled onClick={handleClick}>Кнопка</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('opacity-50')
    expect(button).toHaveClass('cursor-not-allowed')
    
    fireEvent.click(button)
    expect(handleClick).not.toHaveBeenCalled()
  })

  // Тест состояния loading
  it('отображает спиннер в состоянии loading', () => {
    render(<Button loading>Загрузка</Button>)
    
    const button = screen.getByRole('button')
    const spinner = button.querySelector('svg')
    
    expect(button).toBeDisabled()
    expect(button).toHaveClass('cursor-wait')
    expect(spinner).toBeInTheDocument()
    expect(spinner).toHaveClass('animate-spin')
  })

  // Тест типа кнопки
  it('применяет правильный type', () => {
    render(<Button type="submit">Отправить</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'submit')
  })

  // Тест кастомных классов
  it('применяет дополнительные CSS классы', () => {
    const customClass = 'my-custom-class'
    
    render(<Button className={customClass}>Кнопка</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass(customClass)
  })

  // Тест default props
  it('использует значения по умолчанию', () => {
    render(<Button>Кнопка</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'button')
    expect(button).toHaveClass('bg-blue-600') // primary variant
    expect(button).toHaveClass('px-4') // md size
    expect(button).toHaveClass('py-2') // md size
  })
})