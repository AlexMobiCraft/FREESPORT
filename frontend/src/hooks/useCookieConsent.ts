'use client';

/**
 * Хук согласия на cookie (Story 41.1).
 *
 * Состояние хранится во внешнем модульном сторе и читается через
 * useSyncExternalStore. Так баннер из корневого layout и кнопка «Настройки
 * cookie» из подвала — компоненты разных поддеревьев — разделяют одно
 * состояние: нажатие в подвале открывает баннер без перезагрузки страницы.
 *
 * ВАЖНО для будущей аналитики: счётчики (Яндекс.Метрика и прочее)
 * подключаются ТОЛЬКО при `status === 'accepted'`, а не при
 * `status !== 'declined'` — иначе посетитель, не сделавший выбор, будет
 * отслеживаться без согласия.
 */

import { useSyncExternalStore } from 'react';

/**
 * Статус согласия.
 * - `unknown` — хранилище ещё не читали (серверный рендер и первый клиентский
 *   кадр). Это НЕ «выбор не сделан».
 * - `unset` — выбор не сделан.
 * - `accepted` / `declined` — выбор посетителя.
 */
export type CookieConsentStatus = 'unknown' | 'unset' | 'accepted' | 'declined';

const STORAGE_KEY = 'cookie_consent';
const LEGACY_STORAGE_KEY = 'cookie_consent_accepted';
const LEGACY_ACCEPTED_VALUE = '1';

interface CookieConsentSnapshot {
  status: CookieConsentStatus;
  /** Баннер открыт принудительно из подвала. В localStorage не пишется. */
  isForced: boolean;
}

/** Снимок для серверного рендера: статус «ещё не читали хранилище». */
const SERVER_SNAPSHOT: CookieConsentSnapshot = Object.freeze({
  status: 'unknown',
  isForced: false,
});

let snapshot: CookieConsentSnapshot = SERVER_SNAPSHOT;
const listeners = new Set<() => void>();

/**
 * Элемент, из которого баннер открыли принудительно, — чтобы вернуть ему фокус
 * после закрытия. Хранится ВНЕ снимка: DOM-узел в рендере не участвует, и
 * попадание его в снимок означало бы лишние ре-рендеры потребителей.
 */
let forcedTrigger: HTMLElement | null = null;

/**
 * Снимок пересоздаётся ТОЛЬКО здесь. getSnapshot обязан возвращать стабильную
 * ссылку, иначе useSyncExternalStore уходит в бесконечный ре-рендер.
 */
function setSnapshot(next: Partial<CookieConsentSnapshot>): void {
  snapshot = { ...snapshot, ...next };
  listeners.forEach(listener => listener());
}

/** Распознаёт значение хранилища; всё неизвестное трактуется как «выбор не сделан». */
function parseStatus(raw: string | null): CookieConsentStatus {
  return raw === 'accepted' || raw === 'declined' ? raw : 'unset';
}

/**
 * Записывает выбор в хранилище. Сбой записи не считается фатальным:
 * статус остаётся в памяти до полной перезагрузки страницы (AC5).
 */
function persist(status: 'accepted' | 'declined'): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, status);
    // Старый ключ после успешной записи нового больше не нужен.
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch (error) {
    console.error('useCookieConsent: запись localStorage не удалась', error);
  }
}

/**
 * Читает состояние из хранилища при первой подписке.
 *
 * Приоритет: валидное значение нового ключа → legacy-ключ `'1'` → «выбор не
 * сделан». Legacy-значение мигрирует в новый формат; старый ключ удаляется
 * только после успешной записи нового, а сбой этой записи не сбрасывает уже
 * распознанное согласие и логируется как ошибка ЗАПИСИ, а не чтения.
 */
function readFromStorage(): void {
  if (typeof window === 'undefined') {
    setSnapshot({ status: 'unset' });
    return;
  }

  let status: CookieConsentStatus;
  let legacyValue: string | null = null;

  try {
    status = parseStatus(window.localStorage.getItem(STORAGE_KEY));
    if (status === 'unset') {
      legacyValue = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    }
  } catch (error) {
    console.error('useCookieConsent: чтение localStorage не удалось', error);
    setSnapshot({ status: 'unset' });
    return;
  }

  if (status === 'unset' && legacyValue === LEGACY_ACCEPTED_VALUE) {
    // Посетитель, принявший cookie до этой стори, баннер повторно не увидит.
    setSnapshot({ status: 'accepted' });
    persist('accepted');
    return;
  }

  setSnapshot({ status });
}

/**
 * Согласие, данное в другой вкладке, применяется и здесь.
 *
 * Учитывается только `localStorage`: событие `storage` приходит и от
 * `sessionStorage`, где одноимённый ключ согласием не является. Событие с
 * `key === null` — это `localStorage.clear()` в другой вкладке; без его
 * обработки здесь остался бы устаревший статус и баннер больше не показался
 * бы. Обратно в хранилище обработчик ничего не пишет.
 */
function handleStorageEvent(event: StorageEvent): void {
  if (typeof window === 'undefined' || event.storageArea !== window.localStorage) {
    return;
  }

  const isFullClear = event.key === null;
  if (!isFullClear && event.key !== STORAGE_KEY) {
    return;
  }

  const nextStatus = isFullClear ? 'unset' : parseStatus(event.newValue);
  // Событие без фактического изменения не должно создавать новый снимок.
  if (nextStatus === snapshot.status && !snapshot.isForced) {
    return;
  }

  setSnapshot({ status: nextStatus, isForced: false });
}

/**
 * Подписка на стор. Хранилище читается лениво — при первой подписке,
 * а не в useEffect каждого потребителя.
 */
function subscribe(listener: () => void): () => void {
  listeners.add(listener);

  if (listeners.size === 1 && typeof window !== 'undefined') {
    window.addEventListener('storage', handleStorageEvent);
  }

  if (snapshot.status === 'unknown') {
    readFromStorage();
  }

  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && typeof window !== 'undefined') {
      window.removeEventListener('storage', handleStorageEvent);
    }
  };
}

function getSnapshot(): CookieConsentSnapshot {
  return snapshot;
}

function getServerSnapshot(): CookieConsentSnapshot {
  return SERVER_SNAPSHOT;
}

/** Зафиксировать согласие. */
function accept(): void {
  persist('accepted');
  setSnapshot({ status: 'accepted', isForced: false });
}

/** Зафиксировать отказ. */
function decline(): void {
  persist('declined');
  setSnapshot({ status: 'declined', isForced: false });
}

/**
 * Открыть баннер заново, не стирая сохранённый выбор.
 *
 * @param trigger элемент, инициировавший открытие. Баннер вернёт ему фокус,
 * когда закроется: иначе после выбора фокус остаётся на `body` и клавиатурный
 * пользователь теряет позицию в подвале (AC6).
 */
function reopen(trigger?: HTMLElement | null): void {
  forcedTrigger = trigger ?? null;
  setSnapshot({ isForced: true });
}

/**
 * Забирает элемент-инициатор и обнуляет его: фокус возвращается ровно один раз.
 * Внутренний контракт хука и баннера, а не публичный API страниц.
 */
export function consumeCookieConsentTrigger(): HTMLElement | null {
  const trigger = forcedTrigger;
  forcedTrigger = null;
  return trigger;
}

/**
 * Сброс модульного стора. ТОЛЬКО ДЛЯ ТЕСТОВ.
 *
 * Состояние стора переживает размонтирование компонентов, поэтому каждый
 * тестовый файл, использующий хук, обязан звать этот сброс в beforeEach —
 * иначе тесты начнут зависеть от порядка выполнения. Очистку самого
 * localStorage хелпер на себя не берёт: это ответственность теста.
 */
export function __resetCookieConsentStoreForTests(): void {
  snapshot = SERVER_SNAPSHOT;
  listeners.clear();
  forcedTrigger = null;
  if (typeof window !== 'undefined') {
    window.removeEventListener('storage', handleStorageEvent);
  }
}

export interface UseCookieConsentReturn {
  /** Текущий статус согласия. */
  status: CookieConsentStatus;
  /** Хранилище прочитано (статус отличен от `unknown`). */
  isLoaded: boolean;
  /** Баннер открыт принудительно кнопкой «Настройки cookie». */
  isForced: boolean;
  /** Баннер должен отображаться. */
  isBannerVisible: boolean;
  /** Зафиксировать согласие. */
  accept: () => void;
  /** Зафиксировать отказ. */
  decline: () => void;
  /**
   * Открыть баннер заново, не стирая сохранённый выбор. Переданный элемент
   * получит фокус обратно после закрытия баннера.
   */
  reopen: (trigger?: HTMLElement | null) => void;
}

export function useCookieConsent(): UseCookieConsentReturn {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const isLoaded = state.status !== 'unknown';

  return {
    status: state.status,
    isLoaded,
    isForced: state.isForced,
    isBannerVisible: isLoaded && (state.status === 'unset' || state.isForced),
    accept,
    decline,
    reopen,
  };
}
