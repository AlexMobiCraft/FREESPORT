/**
 * Страница «Политика обработки персональных данных» (/privacy-policy).
 */

import React from 'react';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Breadcrumb, Card } from '@/components/ui';

interface PageData {
  title: string;
  slug: string;
  content: string;
  seo_title?: string;
  seo_description?: string;
  is_published?: boolean;
}

const DEFAULT_TITLE = 'Политика обработки персональных данных | FREESPORT';
const PRIVACY_POLICY_ENDPOINT = '/pages/privacy-policy/';

function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
}

async function fetchPrivacyPolicy(): Promise<PageData | null> {
  const res = await fetch(`${getApiUrl()}${PRIVACY_POLICY_ENDPOINT}`, {
    next: { revalidate: 3600 },
  });

  if (!res.ok) {
    return null;
  }

  return res.json();
}

export async function generateMetadata(): Promise<Metadata> {
  const page = await fetchPrivacyPolicy();

  return {
    title: page?.seo_title || DEFAULT_TITLE,
    description: page?.seo_description || '',
  };
}

const breadcrumbItems = [
  { label: 'Главная', href: '/' },
  { label: 'Политика обработки персональных данных' },
];

export default async function PrivacyPolicyPage() {
  const page = await fetchPrivacyPolicy();

  if (!page || page.is_published === false) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-neutral-100">
      <div className="container mx-auto px-4 py-4">
        <Breadcrumb items={breadcrumbItems} />
      </div>

      <section className="bg-white py-8 sm:py-12">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-headline-l sm:text-headline-xl font-bold text-text-primary">
            {page.title}
          </h1>
        </div>
      </section>

      <section className="container mx-auto px-4 py-8 sm:py-12">
        <Card className="p-6 sm:p-10">
          <div
            className="prose prose-neutral max-w-none text-text-primary"
            dangerouslySetInnerHTML={{ __html: page.content }}
          />
        </Card>
      </section>
    </div>
  );
}
