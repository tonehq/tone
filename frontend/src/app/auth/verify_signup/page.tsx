'use client';

import { Suspense, useState } from 'react';

import { useRouter, useSearchParams } from 'next/navigation';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/Form';
import axios from '../../../utils/axios';
import { handleApiError } from '../../../utils/helpers';
import { showToast } from '../../../utils/toast';
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
      <div className="w-full max-w-[400px]">
        <h2 className="mb-4 text-3xl font-semibold text-foreground">Email Verification</h2>
        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <div className="mb-6">
            <p className="text-[15px] text-foreground">
              To complete the verification process, please click the button below:
            </p>
          </div>
          <div className="mt-2 flex flex-col gap-2">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Accept
            </CustomButton>
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
