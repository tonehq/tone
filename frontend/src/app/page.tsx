'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { LOGIN_DATA, ROUTE_HOME, ROUTE_LOGIN } from '@/constants';
import { AppLoader } from '@/components/shared';

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    // The access token is an httpOnly cookie JS can't read; use the readable
    // login_data payload as the client-side signal. The server-side middleware
    // is the authoritative guard and will bounce an invalid session anyway.
    const hasSession = typeof window !== 'undefined' && !!localStorage.getItem(LOGIN_DATA);
    router.replace(hasSession ? ROUTE_HOME : ROUTE_LOGIN);
  }, [router]);

  return <AppLoader />;
}
