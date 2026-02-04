import { Suspense } from 'react';
import InnerLoginPage from './LoginPage';

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <InnerLoginPage />
    </Suspense>
  );
}
