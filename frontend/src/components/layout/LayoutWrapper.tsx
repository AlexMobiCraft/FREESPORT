'use client';

import { usePathname } from 'next/navigation';

export default function LayoutWrapper({
  children,
  header,
  footer,
}: {
  children: React.ReactNode;
  header: React.ReactNode;
  footer: React.ReactNode;
}) {
  const pathname = usePathname();
  const isHomePage = pathname === '/';
  const isElectricTestPage = pathname === '/electric-orange-test';

  if (isHomePage || isElectricTestPage) {
    return <main className="flex-grow">{children}</main>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {header}
      <main className="flex-grow relative z-0">{children}</main>
      {footer}
    </div>
  );
}
