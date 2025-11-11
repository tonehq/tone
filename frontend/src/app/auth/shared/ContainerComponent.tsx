'use client';

import { Box } from '@mui/material';

const Container = ({ children }: { children: React.ReactNode }) => (
  <Box
    sx={{
      display: 'flex',
      width: '100vw',
      height: '100vh',
      overflow: 'hidden',
    }}
  >
    {/* Left side */}
    <Box
      sx={{
        width: '50%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Box
        sx={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 2,
          boxShadow: 2,
        }}
      >
        {children}
      </Box>
    </Box>

    {/* Right side */}
    <Box
      sx={{
        width: '50%',
        height: '100%',
      }}
    >
      <Box
        component="img"
        src="https://cdn.builder.io/api/v1/image/assets/TEMP/064d49d468d0952bd0a54eff0df8fb9a191373a750f515c5d402d20433ce4293?apiKey=99f610f079bc4250a85747146003507a&&apiKey=99f610f079bc4250a85747146003507a"
        alt="app logo"
        sx={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />
    </Box>
  </Box>
);

export default Container;
