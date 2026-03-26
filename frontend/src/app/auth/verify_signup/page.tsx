'use client';

import { CheckCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';

import { CustomButton } from '@/components/shared';
import axios from '@/utils/axios';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import Container from '../shared/ContainerComponent';

const EmailVerificationContent = () => {
  const [loader, setLoader] = useState(false);
  const params = useSearchParams();
  const router = useRouter();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get(
        `/auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}`,
      );
      setLoader(false);
      if (res) {
        showToast.success('Email Verified', 'Your email has been verified successfully', 4);
        const inviteRedirect = localStorage.getItem('invite_redirect');
        if (inviteRedirect) {
          localStorage.removeItem('invite_redirect');
          router.push(inviteRedirect);
        } else {
          router.push('/auth/login');
        }
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px] animate-page text-center">
        {/* Icon */}
        <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-primary/10">
          <CheckCircle className="size-8 text-primary" />
        </div>

        <h2 className="mb-2 text-2xl font-semibold tracking-tight text-foreground">
          Email Verification
        </h2>
        <p className="mb-8 text-sm text-muted-foreground">
          To complete the verification process, please click the button below:
        </p>

        <CustomButton loading={loader} type="primary" onClick={handleSubmit} fullWidth>
          Verify Email
        </CustomButton>
      </div>
    </Container>
  );
};

const EmailVerification: React.FC = () => (
  <Suspense fallback={null}>
    <EmailVerificationContent />
  </Suspense>
);

export default EmailVerification;
