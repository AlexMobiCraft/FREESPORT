import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Toaster } from 'react-hot-toast';
import './globals.css';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin', 'cyrillic'],
});

export const metadata: Metadata = {
  title: 'FREESPORT Platform | B2B/B2C спортивные товары',
  description:
    'Ведущая платформа продаж спортивных товаров. B2B/B2C решения для тренеров, федераций и дистрибьюторов.',
  keywords: 'спорт, товары, оптом, B2B, B2C, тренажеры, спортивный инвентарь',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className={`${inter.variable} font-sans antialiased`}>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-grow">{children}</main>
          <Footer />
        </div>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#FFFFFF',
              color: '#1B1B1B',
              border: '1px solid #E0E0E0',
              borderRadius: '12px',
              fontSize: '16px',
            },
            success: {
              iconTheme: {
                primary: '#1F7A1F',
                secondary: '#E0F5E0',
              },
            },
            error: {
              iconTheme: {
                primary: '#C23B3B',
                secondary: '#FFE1E1',
              },
            },
          }}
        />
      </body>
    </html>
  );
}
