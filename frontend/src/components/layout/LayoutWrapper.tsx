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

  if (isHomePage) {
    return <main className="flex-grow">{children}</main>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      {header}
      <main className="relative z-0 flex-grow">{children}</main>
      {footer}
    </div>
  );
}
