/**
 * Fallback-картинка hero темы Electric (стори 41.6, AC5).
 *
 * Компонент подставляет `/hero-fallback.jpg`, когда баннер из API не пришёл:
 * `currentBanner?.image_url || '/hero-fallback.jpg'`. До стори 41.6 файл носил
 * имя соцпревью, хотя на деле работал заглушкой hero. Простое удаление файла
 * (как предполагал текст эпика) дало бы битую картинку ровно в момент
 * недоступности API баннеров.
 *
 * Проверяется именно эта ветка: SSR отдаёт скелетон, а сам fallback виден
 * только после того, как клиентский запрос баннеров завершился ошибкой.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

import { ElectricHeroSection } from '../ElectricHeroSection';
import { useAuthStore } from '@/stores/authStore';
import bannersService from '@/services/bannersService';
import { trackBannerClick, trackBannerView } from '@/services/siteEvents';
import {
  installIntersectionObserverMock,
  type IntersectionObserverMockControls,
} from '@/__mocks__/intersectionObserver';
import type { User } from '@/types/api';

vi.mock('@/stores/authStore');
vi.mock('@/services/bannersService');

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    onClick,
    onAuxClick,
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: React.MouseEventHandler<HTMLAnchorElement>;
    onAuxClick?: React.MouseEventHandler<HTMLAnchorElement>;
  }) => (
    <a href={href} onClick={onClick} onAuxClick={onAuxClick}>
      {children}
    </a>
  ),
}));

// Счётчик показов и кликов для ОРД — проверяется вызов, а не сеть
vi.mock('@/services/siteEvents', () => ({
  trackBannerView: vi.fn(),
  trackBannerClick: vi.fn(),
}));

/** Гость без баннеров из API — состояние, в котором работает fallback */
function mockGuestWithoutBanners(failure: 'error' | 'empty') {
  if (failure === 'error') {
    vi.mocked(bannersService.getActive).mockRejectedValue(new Error('API Error'));
  } else {
    vi.mocked(bannersService.getActive).mockResolvedValue([]);
  }

  vi.mocked(useAuthStore).mockReturnValue({
    user: null,
    isAuthenticated: false,
    accessToken: null,
    setTokens: vi.fn(),
    setUser: vi.fn(),
    logout: vi.fn(),
    getRefreshToken: vi.fn(),
  });
}

describe('ElectricHeroSection: fallback-картинка', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('показывает /hero-fallback.jpg при ошибке API баннеров', async () => {
    mockGuestWithoutBanners('error');

    render(<ElectricHeroSection />);

    const image = await screen.findByAltText('OPTISPORT');
    expect(image).toHaveAttribute('src', '/hero-fallback.jpg');
  });

  it('показывает /hero-fallback.jpg при пустом ответе API баннеров', async () => {
    mockGuestWithoutBanners('empty');

    render(<ElectricHeroSection />);

    const image = await screen.findByAltText('OPTISPORT');
    expect(image).toHaveAttribute('src', '/hero-fallback.jpg');
  });
});

/** Авторизованный клиент с ролью `role` без баннеров из API */
function mockUserWithoutBanners(role: User['role'], failure: 'error' | 'empty') {
  if (failure === 'error') {
    vi.mocked(bannersService.getActive).mockRejectedValue(new Error('API Error'));
  } else {
    vi.mocked(bannersService.getActive).mockResolvedValue([]);
  }

  vi.mocked(useAuthStore).mockReturnValue({
    user: {
      id: 7,
      email: `${role}@test.com`,
      first_name: 'Test',
      last_name: 'B2B',
      phone: '+79001234567',
      role,
    },
    isAuthenticated: true,
    accessToken: 'mock-token',
    setTokens: vi.fn(),
    setUser: vi.fn(),
    logout: vi.fn(),
    getRefreshToken: vi.fn(),
  });
}

// Роли vip, special_price и dealer назначает менеджер или 1С, но резервный баннер у них оптовый, как у
// остальных B2B. Без условия для них баннер откатился бы на универсальный, гостевой.
describe.each(['vip', 'special_price', 'dealer'] as const)(
  'ElectricHeroSection: резервный оптовый баннер для роли %s',
  role => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it.each(['error', 'empty'] as const)('показывает оптовый баннер: %s', async failure => {
      mockUserWithoutBanners(role, failure);

      render(<ElectricHeroSection />);

      expect(await screen.findByText('ОПТОВЫЕ ПОСТАВКИ СПОРТИВНЫХ ТОВАРОВ')).toBeInTheDocument();
      expect(screen.queryByText('OPTISPORT — ВАШ СПОРТИВНЫЙ ПАРТНЁР')).not.toBeInTheDocument();
    });
  }
);


// ---------------------------------------------------------------------------
// Счётчик показов и кликов (отчётность в ОРД)
// ---------------------------------------------------------------------------

const trackedBanners = [
  {
    id: 1,
    type: 'hero' as const,
    title: 'First Banner',
    subtitle: 'First Subtitle',
    image_url: '/media/banners/first.jpg',
    mobile_image_url: '',
    image_alt: 'First banner',
    cta_text: 'Click first',
    cta_link: '/first',
    is_advertisement: false,
    advertiser_name: '',
    advertiser_inn: '',
    erid: '',
  },
  {
    id: 2,
    type: 'hero' as const,
    title: 'Second Banner',
    subtitle: 'Second Subtitle',
    image_url: '/media/banners/second.jpg',
    mobile_image_url: '',
    image_alt: 'Second banner',
    cta_text: 'Click second',
    cta_link: '/second',
    is_advertisement: false,
    advertiser_name: '',
    advertiser_inn: '',
    erid: '',
  },
];

const auxClick = (element: Element, button: number) => {
  act(() => {
    element.dispatchEvent(new MouseEvent('auxclick', { bubbles: true, cancelable: true, button }));
  });
};

describe('ElectricHeroSection — показы и клики', () => {
  let io: IntersectionObserverMockControls;

  // next/image зовёт onLoad после img.decode() — ждём микрозадачи
  const loadImage = async (alt: string) => {
    await act(async () => {
      fireEvent.load(screen.getByAltText(alt));
      await Promise.resolve();
      await Promise.resolve();
    });
  };

  const renderLoaded = async () => {
    vi.mocked(bannersService.getActive).mockResolvedValue(trackedBanners);
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      setTokens: vi.fn(),
      setUser: vi.fn(),
      logout: vi.fn(),
      getRefreshToken: vi.fn(),
    });
    render(<ElectricHeroSection />);
    await screen.findByText('First Banner');
    return screen.getByLabelText('Hero section');
  };

  beforeEach(() => {
    vi.clearAllMocks();
    io = installIntersectionObserverMock();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('засчитывает показ текущего баннера через 1 с после загрузки картинки', async () => {
    const section = await renderLoaded();
    await loadImage('First banner');
    vi.useFakeTimers();

    act(() => io.setIntersection(section, 0.8));
    act(() => vi.advanceTimersByTime(999));
    expect(trackBannerView).not.toHaveBeenCalled();
    act(() => vi.advanceTimersByTime(1));

    expect(vi.mocked(trackBannerView).mock.calls).toEqual([[1]]);
  });

  it('автопрокрутка: новый баннер засчитывается после загрузки своей картинки', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const section = await renderLoaded();
    await loadImage('First banner');
    act(() => io.setIntersection(section, 1));
    act(() => vi.advanceTimersByTime(1000));
    expect(vi.mocked(trackBannerView).mock.calls).toEqual([[1]]);

    // Автопрокрутка через 5 с: тот же DOM-узел, IO повторно не срабатывает
    act(() => vi.advanceTimersByTime(4000));
    expect(screen.getByText('Second Banner')).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(3000));
    // Картинка второго ещё не загрузилась — показ не засчитан
    expect(vi.mocked(trackBannerView).mock.calls).toEqual([[1]]);

    await loadImage('Second banner');
    act(() => vi.advanceTimersByTime(1000));

    expect(vi.mocked(trackBannerView).mock.calls).toEqual([[1], [2]]);
  });

  it('ошибка картинки — показ не засчитан', async () => {
    const section = await renderLoaded();
    act(() => {
      fireEvent.error(screen.getByAltText('First banner'));
    });
    vi.useFakeTimers();

    act(() => io.setIntersection(section, 1));
    act(() => vi.advanceTimersByTime(3000));

    expect(trackBannerView).not.toHaveBeenCalled();
  });

  it('клик по CTA отправляет click текущего баннера', async () => {
    await renderLoaded();

    fireEvent.click(screen.getByText('Click first'));

    expect(trackBannerClick).toHaveBeenCalledWith(1);
  });

  it('открытие средней кнопкой (auxclick) тоже считается кликом, правая кнопка — нет', async () => {
    await renderLoaded();
    const link = screen.getByText('Click first').closest('a') as HTMLAnchorElement;

    auxClick(link, 2);
    expect(trackBannerClick).not.toHaveBeenCalled();

    auxClick(link, 1);
    expect(trackBannerClick).toHaveBeenCalledTimes(1);
    expect(trackBannerClick).toHaveBeenCalledWith(1);
  });

  it('статический fallback-баннер не учитывается', async () => {
    vi.mocked(bannersService.getActive).mockResolvedValue([]);
    vi.mocked(useAuthStore).mockReturnValue({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      setTokens: vi.fn(),
      setUser: vi.fn(),
      logout: vi.fn(),
      getRefreshToken: vi.fn(),
    });
    render(<ElectricHeroSection />);
    const section = await screen.findByLabelText('Hero section');
    vi.useFakeTimers();

    act(() => io.setIntersection(section, 1));
    act(() => vi.advanceTimersByTime(3000));
    fireEvent.click(screen.getAllByRole('link')[0]);

    expect(trackBannerView).not.toHaveBeenCalled();
    expect(trackBannerClick).not.toHaveBeenCalled();
  });
});
