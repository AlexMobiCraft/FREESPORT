/**
 * React Component - Реальный пример из проекта FREESPORT
 * Демонстрирует паттерны TypeScript, Tailwind CSS, состояния loading
 */
import React from 'react';
import type { BaseComponentProps } from '@/types';

// ✅ ПАТТЕРН: TypeScript интерфейсы для props с расширением базовых
interface ButtonProps extends BaseComponentProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

/**
 * ✅ РЕАЛЬНЫЙ ПРИМЕР: Базовый компонент Button 
 * Из frontend/src/components/ui/Button.tsx
 * 
 * КЛЮЧЕВЫЕ ПАТТЕРНЫ:
 * - TypeScript типизация всех props
 * - Tailwind CSS для стилизации
 * - Поддержка loading состояния с спиннером
 * - Spread остальных props (...props)
 * - Условная сборка классов
 */
const Button: React.FC<ButtonProps> = ({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  type = 'button',
  onClick,
  ...props  // ✅ ПАТТЕРН: Spread остальных props
}) => {
  // ✅ ПАТТЕРН: Базовые стили с Tailwind CSS
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  // ✅ ПАТТЕРН: Объект с вариантами стилей
  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    outline: 'border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-blue-500',
    ghost: 'text-gray-700 bg-transparent hover:bg-gray-100 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
  };
  
  // ✅ ПАТТЕРН: Размеры компонента
  const sizeStyles = {
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };
  
  // ✅ ПАТТЕРН: Динамическая сборка классов с фильтрацией
  const buttonClasses = [
    baseStyles,
    variantStyles[variant],
    sizeStyles[size],
    loading && 'cursor-wait',
    className,
  ].filter(Boolean).join(' ');
  
  return (
    <button
      type={type}
      className={buttonClasses}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {/* ✅ ПАТТЕРН: SVG спиннер для loading состояния */}
      {loading && (
        <svg
          className="-ml-1 mr-2 h-4 w-4 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
};

export default Button;

// ✅ ПРИМЕР: Компонент продукта с ролевыми ценами
interface ProductCardProps extends BaseComponentProps {
  product: {
    id: number;
    name: string;
    price: number;
    image: string;
    brand: string;
  };
  userRole?: string;
  onAddToCart?: (productId: number) => void;
}

const ProductCard: React.FC<ProductCardProps> = ({
  product,
  userRole = 'retail',
  onAddToCart,
  className = '',
}) => {
  const [loading, setLoading] = React.useState(false);

  const handleAddToCart = async () => {
    if (!onAddToCart) return;
    
    setLoading(true);
    try {
      await onAddToCart(product.id);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200 ${className}`}>
      <img
        src={product.image}
        alt={product.name}
        className="w-full h-48 object-cover"
      />
      
      <div className="p-4">
        <h3 className="font-semibold text-lg mb-2">{product.name}</h3>
        <p className="text-gray-600 mb-2">{product.brand}</p>
        
        <div className="flex items-center justify-between">
          <span className="text-xl font-bold text-blue-600">
            {product.price.toLocaleString('ru-RU')} ₽
          </span>
          
          <Button
            variant="primary"
            size="sm"
            loading={loading}
            onClick={handleAddToCart}
            disabled={!onAddToCart}
          >
            В корзину
          </Button>
        </div>
      </div>
    </div>
  );
};

// ✅ ШАБЛОН КОМПОНЕНТА ДЛЯ НОВЫХ СУЩНОСТЕЙ
interface YourComponentProps extends BaseComponentProps {
  // Определите ваши props здесь
  title?: string;
  description?: string;
  loading?: boolean;
  onAction?: () => void;
}

const YourComponent: React.FC<YourComponentProps> = ({
  className = '',
  children,
  title,
  description,
  loading = false,
  onAction,
  ...props
}) => {
  // ✅ ПАТТЕРН: Локальное состояние с useState
  const [isExpanded, setIsExpanded] = React.useState(false);

  // ✅ ПАТТЕРН: useEffect для побочных эффектов
  React.useEffect(() => {
    // Ваша логика
  }, []);

  // ✅ ПАТТЕРН: Вычисляемые стили
  const containerClasses = [
    'your-base-classes',
    'p-4',
    'rounded-lg',
    loading && 'opacity-50',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={containerClasses} {...props}>
      {title && (
        <h2 className="text-xl font-semibold mb-2">{title}</h2>
      )}
      
      {description && (
        <p className="text-gray-600 mb-4">{description}</p>
      )}
      
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        children
      )}
      
      {onAction && (
        <Button onClick={onAction} className="mt-4">
          Действие
        </Button>
      )}
    </div>
  );
};

export { ProductCard, YourComponent };
export type { ProductCardProps, YourComponentProps };