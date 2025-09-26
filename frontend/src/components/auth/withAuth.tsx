'use client';

import { ComponentType, FC, useEffect } from 'react';

import Cokkies from 'js-cookie';
import { useRouter } from 'next/navigation';
interface WithAuthProps {
  [key: string]: any;
}

const withAuth = <P extends WithAuthProps>(WrappedComponent: ComponentType<P>) => {
  const WithAuthComponent: FC<P> = (props) => {
    const router = useRouter();

    useEffect(() => {
      if (typeof window !== 'undefined') {
        const token = Cokkies.get('tone_access_token');
        if (!token) {
          router.push('/auth/login');
        }
      }
    }, [router]);

    return <WrappedComponent {...props} />;
  };
  return WithAuthComponent;
};

export default withAuth;
