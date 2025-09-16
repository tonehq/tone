'use client';

import { useEffect, useState } from 'react';

import { useRouter } from 'next/navigation';

import withAuth from '@/components/auth/withAuth';

const IndexPage = () => {
  const router = useRouter();
  const [isInitialMount, setIsInitialMount] = useState(true);

  useEffect(() => {
    if (isInitialMount && typeof window !== 'undefined') {
      setIsInitialMount(false);
      router.push('/Home');
    }
  }, [isInitialMount, router]);

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      router.push('/Home');
      event.preventDefault();
      event.returnValue = '';
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [router]);

  return <div>Loading...</div>;
};

export default withAuth(IndexPage);
