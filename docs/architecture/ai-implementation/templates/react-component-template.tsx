/**
 * Шаблон React компонента для FREESPORT
 * Скопируйте и адаптируйте под ваш компонент
 */
import React from 'react';
import type { BaseComponentProps } from '@/types';

// ===== ТИПЫ И ИНТЕРФЕЙСЫ =====

// TODO: Определите интерфейс для ваших props
interface YourComponentProps extends BaseComponentProps {
  // Основные props
  title?: string;
  description?: string;
  
  // Состояния
  loading?: boolean;
  disabled?: boolean;
  
  // Данные
  data?: YourDataType[];  // TODO: Замените на ваш тип данных
  
  // Функции обратного вызова
  onSubmit?: (data: FormData) => void;
  onCancel?: () => void;
  onChange?: (value: any) => void;
  
  // Стилизация
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  
  // Конфигурация
  showActions?: boolean;
  allowEdit?: boolean;
}

// TODO: Определите тип данных которые использует компонент
interface YourDataType {
  id: number;
  name: string;
  description?: string;
  // Добавьте нужные поля
}

// ===== ОСНОВНОЙ КОМПОНЕНТ =====

/**
 * YourComponent - описание что делает компонент
 * 
 * TODO: Заполните описание функциональности
 * 
 * @param props - Свойства компонента
 * @returns JSX элемент
 */
const YourComponent: React.FC<YourComponentProps> = ({
  className = '',
  children,
  title,
  description,
  loading = false,
  disabled = false,
  data = [],
  onSubmit,
  onCancel,
  onChange,
  variant = 'primary',
  size = 'md',
  showActions = true,
  allowEdit = true,
  ...props  // ✅ ПАТТЕРН: Spread остальных props
}) => {
  
  // ===== СОСТОЯНИЕ =====
  
  const [internalState, setInternalState] = React.useState<string>('');
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [selectedItems, setSelectedItems] = React.useState<number[]>([]);
  
  // TODO: Добавьте нужные состояния
  // const [formData, setFormData] = React.useState<YourFormType>({});
  // const [errors, setErrors] = React.useState<Record<string, string>>({});
  // const [isSubmitting, setIsSubmitting] = React.useState(false);

  // ===== ЭФФЕКТЫ =====
  
  React.useEffect(() => {
    // TODO: Добавьте логику инициализации
    console.log('Component mounted');
    
    // Cleanup функция
    return () => {
      console.log('Component will unmount');
    };
  }, []);

  React.useEffect(() => {
    // TODO: Реакция на изменение props
    if (onChange && internalState) {
      onChange(internalState);
    }
  }, [internalState, onChange]);

  // ===== ВЫЧИСЛЯЕМЫЕ ЗНАЧЕНИЯ =====
  
  const computedValue = React.useMemo(() => {
    // TODO: Добавьте вычисления
    return data.filter(item => item.name.includes(internalState));
  }, [data, internalState]);

  // ===== ОБРАБОТЧИКИ СОБЫТИЙ =====
  
  const handleSubmit = React.useCallback((event: React.FormEvent) => {
    event.preventDefault();
    
    if (onSubmit && !loading && !disabled) {
      // TODO: Подготовьте данные для отправки
      const formData = new FormData();
      // formData.append('field', value);
      
      onSubmit(formData);
    }
  }, [onSubmit, loading, disabled]);

  const handleInputChange = React.useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setInternalState(value);
  }, []);

  const handleToggleExpand = React.useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  const handleItemSelect = React.useCallback((itemId: number) => {
    setSelectedItems(prev => {
      const isSelected = prev.includes(itemId);
      return isSelected 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId];
    });
  }, []);

  // TODO: Добавьте свои обработчики

  // ===== СТИЛИ =====
  
  const baseStyles = 'block w-full transition-all duration-200';
  
  const variantStyles = {
    primary: 'bg-white border border-gray-300 rounded-lg shadow-sm',
    secondary: 'bg-gray-50 border border-gray-200 rounded-lg',
    outline: 'border-2 border-dashed border-gray-300 rounded-lg',
    ghost: 'bg-transparent',
  };

  const sizeStyles = {
    sm: 'p-2 text-sm',
    md: 'p-4 text-base',
    lg: 'p-6 text-lg',
  };

  const containerClasses = [
    baseStyles,
    variantStyles[variant],
    sizeStyles[size],
    loading && 'opacity-50 pointer-events-none',
    disabled && 'opacity-60 cursor-not-allowed',
    className,
  ].filter(Boolean).join(' ');

  // ===== УСЛОВНЫЙ РЕНДЕРИНГ =====
  
  if (loading) {
    return (
      <div className={`${containerClasses} flex items-center justify-center`}>
        <LoadingSpinner />
        <span className="ml-2">Загрузка...</span>
      </div>
    );
  }

  if (!data.length && !children) {
    return (
      <div className={`${containerClasses} text-center text-gray-500`}>
        <p>Нет данных для отображения</p>
      </div>
    );
  }

  // ===== ОСНОВНОЙ РЕНДЕР =====
  
  return (
    <div className={containerClasses} {...props}>
      
      {/* Заголовок */}
      {title && (
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-sm text-gray-600">
              {description}
            </p>
          )}
        </div>
      )}

      {/* Основной контент */}
      <div className="space-y-4">
        
        {/* TODO: Замените на ваш контент */}
        {computedValue.map((item) => (
          <YourItemComponent
            key={item.id}
            item={item}
            selected={selectedItems.includes(item.id)}
            onSelect={() => handleItemSelect(item.id)}
            allowEdit={allowEdit}
          />
        ))}
        
        {children}
      </div>

      {/* Действия */}
      {showActions && (
        <div className="mt-6 flex justify-end space-x-3">
          {onCancel && (
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={loading}
            >
              Отмена
            </Button>
          )}
          
          {onSubmit && (
            <Button
              variant="primary"
              onClick={handleSubmit}
              loading={loading}
              disabled={disabled}
            >
              Сохранить
            </Button>
          )}
        </div>
      )}

      {/* Дополнительный контент */}
      {isExpanded && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p>Дополнительная информация</p>
        </div>
      )}
    </div>
  );
};

export default YourComponent;

// ===== ДОЧЕРНИЕ КОМПОНЕНТЫ =====

interface YourItemComponentProps {
  item: YourDataType;
  selected?: boolean;
  onSelect?: () => void;
  allowEdit?: boolean;
}

const YourItemComponent: React.FC<YourItemComponentProps> = ({
  item,
  selected = false,
  onSelect,
  allowEdit = true,
}) => {
  return (
    <div 
      className={`
        p-3 border rounded-lg cursor-pointer transition-colors
        ${selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}
      `}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium text-gray-900">{item.name}</h3>
          {item.description && (
            <p className="text-sm text-gray-600">{item.description}</p>
          )}
        </div>
        
        {allowEdit && (
          <div className="flex space-x-2">
            <Button size="sm" variant="outline">
              Редактировать
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

// ===== LOADING КОМПОНЕНТ =====

const LoadingSpinner: React.FC = () => (
  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
);

// ===== ХУКИ ДЛЯ КОМПОНЕНТА =====

/**
 * Кастомный хук для работы с данными компонента
 */
const useYourComponentData = () => {
  const [data, setData] = React.useState<YourDataType[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // TODO: Замените на ваш API вызов
      const response = await fetch('/api/your-endpoint/');
      
      if (!response.ok) {
        throw new Error('Ошибка загрузки данных');
      }
      
      const result = await response.json();
      setData(result.results || result);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Неизвестная ошибка');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
};

// ===== ДОПОЛНИТЕЛЬНЫЕ ВАРИАНТЫ КОМПОНЕНТА =====

/**
 * Упрощенная версия компонента только для отображения
 */
export const YourSimpleComponent: React.FC<{
  title: string;
  children: React.ReactNode;
  className?: string;
}> = ({ title, children, className = '' }) => {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      <h3 className="text-lg font-medium text-gray-900 mb-3">{title}</h3>
      {children}
    </div>
  );
};

/**
 * Версия компонента с формой
 */
export const YourFormComponent: React.FC<{
  initialData?: Partial<YourDataType>;
  onSubmit: (data: YourDataType) => void;
  onCancel?: () => void;
}> = ({ initialData, onSubmit, onCancel }) => {
  const [formData, setFormData] = React.useState<Partial<YourDataType>>(
    initialData || {}
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.name) {
      onSubmit(formData as YourDataType);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Название
        </label>
        <input
          type="text"
          value={formData.name || ''}
          onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Описание
        </label>
        <textarea
          value={formData.description || ''}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          rows={3}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex justify-end space-x-3">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            Отмена
          </Button>
        )}
        <Button type="submit" variant="primary">
          Сохранить
        </Button>
      </div>
    </form>
  );
};

// ===== ЭКСПОРТЫ =====

export type { YourComponentProps, YourDataType };
export { useYourComponentData };