'use client';

import React from 'react';
import { MapPin, Check } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { Address } from '@/types/address';

export interface AddressCardOptionProps {
  address: Address;
  selected: boolean;
  onSelect: (id: number) => void;
}

/**
 * Карточка-опция выбора сохранённого адреса в селекторе чекаута.
 *
 * Отличается от business/AddressCard: нет кнопок edit/delete (управление
 * адресами — на странице /profile/addresses), кликабельна целиком, имеет
 * radio-state выделения.
 */
export const AddressCardOption: React.FC<AddressCardOptionProps> = ({
  address,
  selected,
  onSelect,
}) => {
  const handleClick = () => onSelect(address.id);

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={handleClick}
      data-testid="address-card-option"
      data-selected={selected ? 'true' : 'false'}
      className={cn(
        'group relative flex w-full flex-col items-start gap-2 rounded-lg border bg-white p-4 text-left',
        'transition-colors duration-150',
        selected
          ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
          : 'border-gray-200 hover:border-blue-300'
      )}
    >
      <div className="flex w-full items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <MapPin
            className={cn('h-4 w-4 flex-shrink-0', selected ? 'text-blue-600' : 'text-gray-400')}
            aria-hidden="true"
          />
          <span className="truncate text-sm font-semibold text-gray-900">
            {address.full_name || 'Без имени'}
          </span>
        </div>
        {address.is_default && (
          <span className="flex-shrink-0 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
            По умолчанию
          </span>
        )}
      </div>

      <p className="break-words text-sm text-gray-600">{address.full_address}</p>

      {address.phone && <p className="text-xs text-gray-500">{address.phone}</p>}

      {selected && (
        <span
          className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500"
          aria-hidden="true"
        >
          <Check className="h-3 w-3 text-white" strokeWidth={3} />
        </span>
      )}
    </button>
  );
};

AddressCardOption.displayName = 'AddressCardOption';

export default AddressCardOption;
