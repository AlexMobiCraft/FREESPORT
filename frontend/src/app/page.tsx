import { redirect } from 'next/navigation';

const THEME_ROUTES = {
  coming_soon: '/coming-soon',
  blue: '/home',
  electric_orange: '/electric',
} as const;

type ThemeKey = keyof typeof THEME_ROUTES;

export default function RootPage() {
  const activeTheme = (process.env.ACTIVE_THEME || 'coming_soon') as ThemeKey;
  const targetRoute = THEME_ROUTES[activeTheme] || '/coming-soon';
  redirect(targetRoute);
}
