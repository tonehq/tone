'use client';

import { Box, Typography, useTheme } from '@mui/material';
import { Mail } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

const CheckEmailContent = () => {
  const params = useSearchParams();
  const theme = useTheme();
  const email = params.get('email') || 'your email';

  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f9fafb',
        p: 4,
      }}
    >
      <Box
        sx={{
          maxWidth: 400,
          textAlign: 'center',
          backgroundColor: '#ffffff',
          p: 6,
          borderRadius: '5px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        }}
      >
        {/* Icon */}
        <Box
          sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 3,
          }}
        >
          <Mail size={40} color="#8b5cf6" />
        </Box>

        {/* Title */}
        <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
          Check your email
        </Typography>

        {/* Description */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="body1" sx={{ color: theme.palette.text.secondary, mb: 1 }}>
            We&apos;ve sent an email to
          </Typography>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            {email}
          </Typography>
          <Typography variant="body1" sx={{ color: theme.palette.text.secondary, mt: 1 }}>
            Click the link in the email to verify your account.
          </Typography>
        </Box>

        {/* Footer note */}
        <Typography variant="body2" sx={{ color: theme.palette.text.secondary }}>
          Didn&apos;t receive the email? Check your spam folder or{' '}
          <Typography
            component={Link}
            href="/auth/login"
            sx={{
              color: theme.palette.primary.main,
              textDecoration: 'none',
              fontWeight: 500,
              '&:hover': { textDecoration: 'underline' },
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
