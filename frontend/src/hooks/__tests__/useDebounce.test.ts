/**
 * useDebounce Hook Tests
 * Тесты для debounce hook
 */

import { renderHook, waitFor } from '@testing-library/react';
import { useDebounce } from '../useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));

    expect(result.current).toBe('initial');
  });

  it('debounces value changes', () => {
    const { result, rerender } = renderHook(({ value, delay }) => useDebounce(value, delay), {
      initialProps: { value: 'initial', delay: 500 },
    });

    expect(result.current).toBe('initial');

    // Изменяем значение
    rerender({ value: 'updated', delay: 500 });

    // Значение еще не должно измениться
    expect(result.current).toBe('initial');

    // Fast-forward time
    vi.advanceTimersByTime(500);

    // Теперь значение должно обновиться
    waitFor(() => {
      expect(result.current).toBe('updated');
    });
  });

  it('cancels previous timeout on rapid changes', () => {
    const { result, rerender } = renderHook(({ value, delay }) => useDebounce(value, delay), {
      initialProps: { value: 'initial', delay: 500 },
    });

    // Быстрые изменения
    rerender({ value: 'change1', delay: 500 });
    vi.advanceTimersByTime(200);

    rerender({ value: 'change2', delay: 500 });
    vi.advanceTimersByTime(200);

    rerender({ value: 'final', delay: 500 });
    vi.advanceTimersByTime(500);

    // Должно быть только финальное значение
    waitFor(() => {
      expect(result.current).toBe('final');
    });
  });

  it('works with different data types', () => {
    // Number
    const { result: numberResult } = renderHook(() => useDebounce(42, 300));
    expect(numberResult.current).toBe(42);

    // Boolean
    const { result: boolResult } = renderHook(() => useDebounce(true, 300));
    expect(boolResult.current).toBe(true);

    // Object
    const obj = { key: 'value' };
    const { result: objResult } = renderHook(() => useDebounce(obj, 300));
    expect(objResult.current).toBe(obj);

    // Array
    const arr = [1, 2, 3];
    const { result: arrResult } = renderHook(() => useDebounce(arr, 300));
    expect(arrResult.current).toBe(arr);
  });

  it('respects custom delay', () => {
    const { result, rerender } = renderHook(({ value, delay }) => useDebounce(value, delay), {
      initialProps: { value: 'initial', delay: 1000 },
    });

    rerender({ value: 'updated', delay: 1000 });

    // После 500ms значение не должно измениться
    vi.advanceTimersByTime(500);
    expect(result.current).toBe('initial');

    // После 1000ms значение должно обновиться
    vi.advanceTimersByTime(500);
    waitFor(() => {
      expect(result.current).toBe('updated');
    });
  });

  it('cleans up timeout on unmount', () => {
    const { unmount } = renderHook(() => useDebounce('test', 500));

    const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();
  });
});
