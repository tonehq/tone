import { Box, Paper, Typography } from '@mui/material';

const SidebarComponent = ({
  activeSidebar,
  setActiveSidebar,
  settingsSidebar,
}: {
  activeSidebar: string;
  setActiveSidebar: (sidebar: string) => void;
  settingsSidebar: any;
}) => (
  <Box sx={{ width: 200, height: '95vh' }}>
    <Paper sx={{ borderRadius: '5px', height: '100%', overflow: 'hidden', p: 1 }}>
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 2, px: 1, mt: 1 }}>
        Settings
      </Typography>
      {settingsSidebar.map((item: any) => (
        <Box
          key={item.key}
          px={2}
          onClick={() => setActiveSidebar(item.title)}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            py: 1,
            borderRadius: '5px',
            mb: 1,
            cursor: 'pointer',
            ':hover': { backgroundColor: '#f3f4f6' },
            ...(activeSidebar === item.title && {
              backgroundColor: '#f3f4f6',
            }),
          }}
        >
          <item.icon size={18} />
          <Typography sx={{ fontWeight: 500, fontSize: '14px' }}>{item.title}</Typography>
        </Box>
      ))}
    </Paper>
  </Box>
);

export default SidebarComponent;
