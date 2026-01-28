'use client';

import { Suspense, useState } from 'react';

import { Box, Stack, Typography, useTheme } from '@mui/material';
import { useRouter, useSearchParams } from 'next/navigation';

import CustomButton from '@/components/shared/CustomButton';

import axios from '@/utils/axios';
import { useNotification } from '@/utils/shared/notification';

const AcceptInvitationContent = () => {
  const [loader, setLoader] = useState(false);
  const params = useSearchParams();
  const router = useRouter();
  const { notify, contextHolder } = useNotification();
  const theme = useTheme();

  const email = params.get('email') || '';
  const code = params.get('code') || '';
  const orgId = params.get('user_tenant_id') || '';

  const handleAccept = async () => {
    try {
      setLoader(true);
      const res = await axios.get(
        `/api/v1/organization/accept_invitation?email=${encodeURIComponent(email)}&code=${encodeURIComponent(code)}&user_tenant_id=${orgId}`,
      );
      setLoader(false);
      if (res.data) {
        notify.success(
          'Invitation Accepted',
          `You have joined ${res.data.organization?.name || 'the organization'} successfully`,
          4,
          'bottomRight',
        );
        router.push('/auth/login');
      }
    } catch (error) {
      let errorMessage = 'Failed to accept invitation';

      if (
        typeof error === 'object' &&
        error !== null &&
        'response' in error &&
        'data' in (error as any).response &&
        'detail' in (error as any).response.data
      ) {
        errorMessage = (error as any).response.data.detail;
      }
      const inviteUrl = encodeURIComponent(window.location.href);

      if (errorMessage.includes('sign up first')) {
        notify.info(
          'Account Required',
          'Redirecting you to sign up...',
          3,
          'bottomRight',
        );
        setTimeout(() => {
          router.push(`/auth/signup?email=${encodeURIComponent(email)}&redirect=${inviteUrl}`);
        }, 1500);
      } else if (errorMessage.includes('verify your email')) {
        notify.info(
          'Email Verification Required',
          'Please verify your email first, then try again',
          4,
          'bottomRight',
        );
        setTimeout(() => {
          router.push(`/auth/login?email=${encodeURIComponent(email)}&redirect=${inviteUrl}`);
        }, 1500);
      } else {
        notify.error('Invitation Failed', errorMessage, 5, 'bottomRight');
      }
      setLoader(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        width: '100vw',
        height: '100vh',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f9fafb',
      }}
    >
      {contextHolder}
      <Box
        sx={{
          width: '100%',
          maxWidth: 500,
          backgroundColor: '#fff',
          borderRadius: 3,
          border: '1px solid #e5e7eb',
          p: 5,
          textAlign: 'center',
        }}
      >
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: theme.palette.text.primary,
          }}
        >
          Tone
        </Typography>

        <Typography
          variant="h5"
          sx={{
            fontWeight: 600,
            mb: 2,
            color: theme.palette.text.primary,
          }}
        >
          You&apos;ve been invited!
        </Typography>

        <Typography
          variant="body1"
          sx={{
            color: theme.palette.text.secondary,
            mb: 4,
          }}
        >
          You have been invited to join an organization on Tone.
          Click the button below to accept the invitation.
        </Typography>

        <Box
          sx={{
            backgroundColor: '#f3f4f6',
            borderRadius: 2,
            p: 2,
            mb: 4,
          }}
        >
          <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
            Invitation for: <strong>{email}</strong>
          </Typography>
        </Box>

        <Stack spacing={2}>
          <CustomButton
            text="Accept Invitation"
            loading={loader}
            type="primary"
            onClick={handleAccept}
            sx={{ width: '100%' }}
          />
          <CustomButton
            text="Decline"
            loading={false}
            type="default"
            onClick={() => router.push('/')}
            sx={{ width: '100%' }}
          />
        </Stack>

        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.secondary,
            mt: 3,
          }}
        >
          Don&apos;t have an account?{' '}
          <Typography
            component="a"
            href={`/auth/signup?email=${encodeURIComponent(email)}`}
            sx={{
              color: theme.palette.primary.main,
              textDecoration: 'none',
              fontWeight: 500,
              '&:hover': {
                textDecoration: 'underline',
              },
            }}
          >
            Sign up here
          </Typography>
        </Typography>
      </Box>
    </Box>
  );
};

const AcceptInvitationPage = () => (
  <Suspense fallback={null}>
    <AcceptInvitationContent />
  </Suspense>
);

export default AcceptInvitationPage;
