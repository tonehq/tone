'use client';

import { Suspense, useState } from 'react';

import { useRouter, useSearchParams } from 'next/navigation';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/Form';
import axios from '../../../utils/axios';
import { useNotification } from '../../../utils/notification';
import Container from '../shared/ContainerComponent';

const EmailVerificationContent = () => {
  const [loader, setLoader] = useState(false);
  const params = useSearchParams();
  const router = useRouter();
  const { notify, contextHolder } = useNotification();

  const handleSubmit = async () => {
    try {
      setLoader(true);
      const res = await axios.get(
        `/auth/verify_user_email?email=${params.get('email')}&code=${params.get('code')}&user_id=${params.get('user_id')}`,
      );
      setLoader(false);
      if (res) {
        notify.success('Email Verified', 'Your email has been verified successfully', 4);
        const inviteRedirect = localStorage.getItem('invite_redirect');
        if (inviteRedirect) {
          localStorage.removeItem('invite_redirect');
          router.push(inviteRedirect);
        } else {
          router.push('/auth/login');
        }
      }
    } catch (error) {
      let errorMessage = '';

      if (
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        'data' in (error as any).response &&
        'detail' in (error as any).response.data
      ) {
        errorMessage = (error as any).response.data.detail;
      }
      notify.error('Verification Failed', errorMessage || 'Invalid verification link', 5);
      setLoader(false);
    }
  };

  return (
    <Container>
      {contextHolder}
      <div className="w-full max-w-[400px]">
        <h2 className="mb-4 text-3xl font-semibold text-foreground">Email Verification</h2>
        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <div className="mb-6">
            <p className="text-[15px] text-foreground">
              To complete the verification process, please click the button below:
            </p>
          </div>
          <div className="mt-2 flex flex-col gap-2">
            <CustomButton
              text="Accept"
              loading={loader}
              type="primary"
              htmlType="submit"
              fullWidth
            />
          </div>
        </Form>
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
