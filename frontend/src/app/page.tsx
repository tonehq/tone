'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { ACCESS_TOKEN } from '@/constants';
import { AppLoader } from '@/components/shared';

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem(ACCESS_TOKEN) : null;
    router.replace(token ? '/home' : '/login');
  }, [router]);

  return <AppLoader />;
}
