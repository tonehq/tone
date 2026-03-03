'use client';

import { useState } from 'react';
import CustomButton from '../../../components/shared/CustomButton';
import { Form } from '../../../components/shared/Form';
import TextInput from '../../../components/shared/TextInput';
import { forgotPassword } from '../../../services/auth/helper';
import { showToast } from '../../../utils/toast';
import Container from '../shared/ContainerComponent';

const ForgotPasswordPage = () => {
  const [loader, setLoader] = useState(false);

  const handleSubmit = async (value: any) => {
    setLoader(true);
    if (value['email']) {
      try {
        const res: any = await forgotPassword(value['email']);
        if (res) {
          showToast.success('Email Sent', 'Password reset instructions sent to your email', 4);
          setLoader(false);
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
        showToast.error('Request Failed', errorMessage || 'Something went wrong', 5);
        setLoader(false);
      }
    } else {
      setLoader(false);
    }
  };

  return (
    <Container>
      <div className="w-full max-w-[400px]">
        <h4 className="mb-1 text-xl font-semibold">Reset password</h4>
        <p className="mb-4 text-[15px] text-muted-foreground">
          If there&apos;s an account associated with this email, we will send you a link to reset
          your password.
        </p>

        <Form onFinish={handleSubmit} layout="vertical" autoComplete="off">
          <TextInput
            name="email"
            type="email"
            label="Email"
            placeholder="Enter your email"
            isRequired
          />

          <div className="mt-2 flex flex-col gap-2">
            <CustomButton loading={loader} type="primary" htmlType="submit" fullWidth>
              Reset Password
            </CustomButton>
            <CustomButton type="default" fullWidth onClick={() => window.history.back()}>
              Cancel
            </CustomButton>
          </div>
        </Form>
      </div>
    </Container>
  );
};

export default ForgotPasswordPage;
