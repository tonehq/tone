'use client';

import { Suspense } from 'react';

import { Box, Typography, useTheme } from '@mui/material';
import { useSearchParams } from 'next/navigation';

const CheckEmailContent = () => {
  const params = useSearchParams();
  const theme = useTheme();
  const username = params.get('username') || 'User';
  const email = params.get('email') || '';

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
      <Box
        sx={{
          width: '100%',
          maxWidth: 600,
          backgroundColor: '#fff',
          borderRadius: 3,
          border: '1px solid #e5e7eb',
          p: 6,
          textAlign: 'center',
        }}
      >
        {/* Logo */}
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            textAlign: 'left',
            mb: 4,
            color: theme.palette.text.primary,
          }}
        >
          Tone
        </Typography>

        {/* Mail Icon */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            mb: 4,
          }}
        >
          <Box
            sx={{
              position: 'relative',
              width: 160,
              height: 140,
            }}
          >
            {/* Envelope body */}
            <Box
              sx={{
                position: 'absolute',
                bottom: 0,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 140,
                height: 90,
                backgroundColor: '#F5C842',
                borderRadius: '0 0 20px 20px',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: -30,
                  left: 0,
                  right: 0,
                  height: 60,
                  backgroundColor: '#F5C842',
                  clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)',
                  transform: 'scaleY(-1)',
                },
              }}
            />
            {/* Paper coming out */}
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: '50%',
                transform: 'translateX(-50%)',
                width: 100,
                height: 100,
                backgroundColor: '#f3f4f6',
                borderRadius: 3,
                boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 1,
                py: 2,
              }}
            >
              <Box sx={{ width: 50, height: 4, backgroundColor: '#d4a5a5', borderRadius: 1 }} />
              <Box sx={{ width: 50, height: 4, backgroundColor: '#d4a5a5', borderRadius: 1 }} />
              <Box sx={{ width: 50, height: 4, backgroundColor: '#d4a5a5', borderRadius: 1 }} />
            </Box>
          </Box>
        </Box>

        {/* Greeting */}
        <Typography
          variant="h4"
          sx={{
            fontWeight: 700,
            mb: 1,
            color: theme.palette.text.primary,
          }}
        >
          Hi! {username}
        </Typography>

        {/* Welcome message */}
        <Typography
          variant="h5"
          sx={{
            fontWeight: 600,
            mb: 2,
            color: theme.palette.text.primary,
          }}
        >
          Welcome to Tone
        </Typography>

        {/* Description */}
        <Typography
          variant="body1"
          sx={{
            color: theme.palette.text.secondary,
            mb: 4,
            maxWidth: 400,
            mx: 'auto',
            lineHeight: 1.6,
          }}
        >
          Tone helps you manage your organization efficiently with powerful tools
          for team collaboration and productivity.
        </Typography>

        {/* Check email instruction */}
        <Box
          sx={{
            backgroundColor: '#f3f4f6',
            borderRadius: 2,
            p: 3,
            mb: 3,
          }}
        >
          <Typography
            variant="body1"
            sx={{
              fontWeight: 500,
              color: theme.palette.text.primary,
            }}
          >
            Please check your email
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.secondary,
              mt: 1,
            }}
          >
            We have sent a verification link to <strong>{email}</strong>.
            Click the link in the email to verify your account.
          </Typography>
        </Box>

        {/* Footer note */}
        <Typography
          variant="body2"
          sx={{
            color: theme.palette.text.secondary,
          }}
        >
          Didn&apos;t receive the email? Check your spam folder or{' '}
          <Typography
            component="a"
            href="/auth/login"
            sx={{
              color: theme.palette.primary.main,
              textDecoration: 'none',
              fontWeight: 500,
              '&:hover': {
                textDecoration: 'underline',
              },
            }}
          >
            try again
          </Typography>
        </Typography>
      </Box>
    </Box>
  );
};

const CheckEmailPage = () => (
  <Suspense fallback={null}>
    <CheckEmailContent />
  </Suspense>
);

export default CheckEmailPage;
