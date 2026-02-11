'use client';

import { Box, useTheme } from '@mui/material';
import React from 'react';

interface ContainerProps {
  children: React.ReactNode;
}

const Container: React.FC<ContainerProps> = ({ children }) => {
  const _theme = useTheme();

  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        backgroundColor: '#f9fafb',
      }}
    >
      {/* Left Side - Form */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          p: 4,
          backgroundColor: '#ffffff',
        }}
      >
        {children}
      </Box>

      {/* Right Side - Branding */}
      <Box
        sx={{
          flex: 1,
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          p: 4,
          background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 50%, #ddd6fe 100%)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Logo */}
        <Box
          sx={{
            position: 'absolute',
            top: 32,
            left: 32,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Box
              sx={{
                width: 32,
                height: 32,
                backgroundColor: '#1f2937',
                borderRadius: '5px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                fontWeight: 700,
                fontSize: '1.25rem',
              }}
            >
              S
            </Box>
            <Box
              component="span"
              sx={{
                fontWeight: 700,
                fontSize: '1.25rem',
                color: '#1f2937',
              }}
            >
              Synthflow
            </Box>
          </Box>
        </Box>

        {/* Main Content */}
        <Box sx={{ textAlign: 'center', maxWidth: 500, px: 4 }}>
          {/* Badges */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              gap: 2,
              mb: 4,
            }}
          >
            {['AI Agent Leader', 'High Performer', 'High Performer'].map((badge, index) => (
              <Box
                key={index}
                sx={{
                  backgroundColor: '#ffffff',
                  borderRadius: '5px',
                  p: 1.5,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                }}
              >
                <Box
                  sx={{
                    fontSize: '0.6rem',
                    color: '#f97316',
                    fontWeight: 600,
                    mb: 0.5,
                  }}
                >
                  WINTER 2026
                </Box>
                <Box
                  sx={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    color: index === 0 ? '#f97316' : '#ef4444',
                  }}
                >
                  {badge}
                </Box>
              </Box>
            ))}
          </Box>

          {/* Headline */}
          <Box
            sx={{
              fontSize: '3.5rem',
              fontWeight: 700,
              color: '#1f2937',
              lineHeight: 1.1,
              mb: 3,
            }}
          >
            The Future
            <br />
            of Voice AI
          </Box>

          {/* Rating */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: 3,
              mb: 4,
              color: '#6b7280',
              fontSize: '0.875rem',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box component="span" sx={{ color: '#fbbf24' }}>
                ★
              </Box>
              4.4★ 200+ reviews
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box
                sx={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  backgroundColor: '#22c55e',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                  fontSize: '0.6rem',
                }}
              >
                G
              </Box>
              4.5★ 1000+ reviews
            </Box>
          </Box>

          {/* Testimonials */}
          <Box
            sx={{
              display: 'flex',
              gap: 2,
              mt: 4,
            }}
          >
            {[
              '"The AI assistant has dramatically improved how we manage our schedules."',
              '"Synthflow\'s Voice AI Agents help us book more demos faster."',
            ].map((quote, index) => (
              <Box
                key={index}
                sx={{
                  flex: 1,
                  backgroundColor: '#ffffff',
                  borderRadius: '5px',
                  p: 2,
                  fontSize: '0.75rem',
                  color: '#4b5563',
                  textAlign: 'left',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                }}
              >
                {quote}
              </Box>
            ))}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Container;
