import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { B2BRegisterForm } from '../B2BRegisterForm';
import authService from '@/services/authService';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

vi.mock('@/services/authService', () => ({
  default: {
    registerB2B: vi.fn(),
    refreshToken: vi.fn(),
  },
}));

describe('B2BRegisterForm consent checkboxes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  const acceptPdpConsent = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(
      screen.getByRole('checkbox', { name: /обработку моих персональных данных/i })
    );
  };

  const getMarketingConsent = () =>
    screen.getByRole('checkbox', {
      name: /получать рекламные и информационные рассылки от freesport/i,
    });

  const fillValidB2BForm = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.type(screen.getByLabelText(/имя/i), 'Иван');
    await user.type(screen.getByLabelText(/фамилия/i), 'Петров');
    await user.type(screen.getByLabelText(/электронная почта/i), 'b2b@example.com');
    await user.type(screen.getByLabelText(/телефон/i), '+79991234567');
    await user.type(screen.getByLabelText(/название компании/i), 'ООО Спорт');
    await user.type(screen.getByLabelText(/инн/i), '1234567890');
    await user.type(screen.getByLabelText(/огрн/i), '1234567890123');
    await user.type(screen.getByLabelText(/юридический адрес/i), 'г. Москва, ул. Тестовая, 1');
    await user.type(screen.getByLabelText(/^пароль$/i), 'SecurePass123');
    await user.type(screen.getByLabelText(/подтверждение пароля/i), 'SecurePass123');
  };

  test('should render pdp consent checkbox with privacy policy link inside clickable label', async () => {
    const user = userEvent.setup();
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    render(<B2BRegisterForm />);

    const pdpCheckbox = screen.getByRole('checkbox', {
      name: /обработку моих персональных данных/i,
    });
    expect(pdpCheckbox).toBeInTheDocument();
    const link = screen.getByRole('link', {
      name: /обработку моих персональных данных/i,
    });
    expect(link).toHaveAttribute('href', '/privacy-policy');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    const label = link.closest('label');
    expect(label).not.toBeNull();

    await user.click(label!);
    expect(pdpCheckbox).toBeChecked();

    await user.click(link);
    expect(pdpCheckbox).toBeChecked();
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/privacy-policy'),
      '_blank',
      'noopener,noreferrer'
    );
    openSpy.mockRestore();
  });

  test('should block submit without pdp consent', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(
      (await screen.findAllByText(/необходимо согласие на обработку персональных данных/i))
        .length
    ).toBeGreaterThan(0);
    expect(mockRegisterB2B).not.toHaveBeenCalled();
  });

  test('should submit pdp_consent true and marketing_consent false when marketing unchecked', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    vi.mocked(authService.refreshToken).mockResolvedValue({ access: 'access-token' });
    mockRegisterB2B.mockResolvedValue({
      access: '',
      refresh: '',
      user: {
        id: 10,
        email: 'b2b@example.com',
        first_name: 'Иван',
        last_name: 'Петров',
        phone: '+79991234567',
        role: 'wholesale_level1',
        is_verified: false,
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    await waitFor(() => {
      expect(mockRegisterB2B).toHaveBeenCalledWith(
        expect.objectContaining({
          pdp_consent: true,
          marketing_consent: false,
        })
      );
    });
    expect(authService.refreshToken).not.toHaveBeenCalled();
    expect(await screen.findByText(/заявка на рассмотрении/i)).toBeInTheDocument();
  });

  test('should show pending state even when refresh token is unavailable for pending B2B user', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    vi.mocked(authService.refreshToken).mockRejectedValue(new Error('No refresh token'));
    mockRegisterB2B.mockResolvedValue({
      access: '',
      refresh: '',
      user: {
        id: 10,
        email: 'b2b@example.com',
        first_name: 'Иван',
        last_name: 'Петров',
        phone: '+79991234567',
        role: 'wholesale_level1',
        is_verified: false,
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(await screen.findByText(/заявка на рассмотрении/i)).toBeInTheDocument();
    expect(authService.refreshToken).not.toHaveBeenCalled();
  });

  test('should call onSuccess before showing pending state for pending B2B user', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    const mockOnSuccess = vi.fn();
    mockRegisterB2B.mockResolvedValue({
      access: '',
      refresh: '',
      user: {
        id: 10,
        email: 'b2b@example.com',
        first_name: 'Иван',
        last_name: 'Петров',
        phone: '+79991234567',
        role: 'wholesale_level1',
        is_verified: false,
      },
    });

    render(<B2BRegisterForm onSuccess={mockOnSuccess} redirectUrl="/account" />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(await screen.findByText(/заявка на рассмотрении/i)).toBeInTheDocument();
    expect(mockOnSuccess).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalledWith('/account');
  });

  test('should submit marketing_consent true when checked', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    vi.mocked(authService.refreshToken).mockResolvedValue({ access: 'access-token' });
    mockRegisterB2B.mockResolvedValue({
      access: '',
      refresh: '',
      user: {
        id: 10,
        email: 'b2b@example.com',
        first_name: 'Иван',
        last_name: 'Петров',
        phone: '+79991234567',
        role: 'wholesale_level1',
        is_verified: false,
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(getMarketingConsent());
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    await waitFor(() => {
      expect(mockRegisterB2B).toHaveBeenCalledWith(
        expect.objectContaining({
          pdp_consent: true,
          marketing_consent: true,
        })
      );
    });
  });

  test('should expose associated labels and alert for pdp validation error', async () => {
    const user = userEvent.setup();
    render(<B2BRegisterForm />);

    expect(getMarketingConsent()).not.toBeChecked();
    await fillValidB2BForm(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/необходимо согласие/i);
  });

  test('should display backend pdp consent validation error', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    mockRegisterB2B.mockRejectedValue({
      response: {
        status: 400,
        data: { pdp_consent: ['Необходимо согласие на обработку персональных данных.'] },
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(
      (await screen.findAllByText(/необходимо согласие на обработку персональных данных/i))
        .length
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole('checkbox', { name: /обработку моих персональных данных/i })
    ).toHaveAccessibleDescription(/необходимо согласие на обработку персональных данных/i);
  });

  test('should show first backend validation error instead of hard-coded pdp priority', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    mockRegisterB2B.mockRejectedValue({
      response: {
        status: 400,
        data: {
          email: ['Пользователь с таким email уже существует.'],
          pdp_consent: ['Необходимо согласие на обработку персональных данных.'],
        },
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(
      await screen.findByText(/пользователь с таким email уже существует/i)
    ).toBeInTheDocument();
  });

  test('should surface nested backend validation errors', async () => {
    const user = userEvent.setup();
    const mockRegisterB2B = vi.mocked(authService.registerB2B);
    mockRegisterB2B.mockRejectedValue({
      response: {
        status: 400,
        data: {
          company: {
            tax_id: ['Некорректный ИНН компании'],
          },
        },
      },
    });

    render(<B2BRegisterForm />);

    await fillValidB2BForm(user);
    await acceptPdpConsent(user);
    await user.click(screen.getByRole('button', { name: /отправить заявку/i }));

    expect(await screen.findByText(/некорректный инн компании/i)).toBeInTheDocument();
  });
});
