import {
  Avatar,
  Box,
  ClickAwayListener,
  Divider,
  Grow,
  ListItemIcon,
  MenuItem,
  MenuList,
  Paper,
  Popper,
  Typography,
  useTheme,
} from '@mui/material';
import * as React from 'react';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAtom, useSetAtom } from 'jotai';
import { startCase } from 'lodash';
import { ChevronDown, User } from 'lucide-react';

export default function ProfileMenu(props: any) {
  const { isExpanded } = props;
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);
  const anchorRef = React.useRef<HTMLButtonElement>(null);

  const [authState] = useAtom(authAtom);
  const getCurrentUser = useSetAtom(getCurrentUserAtom);
  const logout = useSetAtom(logoutAtom);

  React.useEffect(() => {
    if (!authState.user && !authState.isLoading) {
      getCurrentUser();
    }
  }, [authState.user, authState.isLoading, getCurrentUser]);

  const handleLogout = () => {
    logout();
  };

  const handleToggle = () => setOpen((prev) => !prev);

  const handleClose = (event: Event | React.SyntheticEvent) => {
    if (anchorRef.current?.contains(event.target as HTMLElement)) return;
    setOpen(false);
  };

  const userEmail = authState?.user?.email;

  const menuItemSx = {
    '&:hover': {
      bgcolor: 'grey.200',
    },
  };

  const logoutMenuItemSx = {
    color: 'error.main',
    '& .MuiListItemIcon-root': {
      color: 'error.main',
    },
    '&:hover': {
      bgcolor: 'rgba(244, 67, 54, 0.08)', // Light error bg on hover; tweak as needed
      color: 'error.main',
      '& .MuiListItemIcon-root': {
        color: 'error.main',
      },
    },
  };

  return (
    <Box>
      {/* Trigger button */}
      <Box
        ref={anchorRef}
        onClick={handleToggle}
        sx={{
          display: 'flex',
          alignItems: 'center',
          borderRadius: 1,
          px: 1.5,
          py: 1.5,
          gap: 1,
          cursor: 'pointer',
          textTransform: 'none',
          transition: 'background 0.15s',
          userSelect: 'none',
        }}
      >
        {isExpanded ? (
          <Box
            sx={{
              mt: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              px: 1,
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                backgroundColor: '#f59e0b',
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
            >
              {authState?.user?.first_name
                ? startCase(authState?.user?.first_name.charAt(0))
                : authState?.user?.email
                  ? authState?.user?.email.charAt(0).toUpperCase()
                  : ''}
            </Avatar>
            <Box
              sx={{
                maxWidth: 140, // set as appropriate for your design
                overflow: 'hidden',
              }}
            >
              <Typography
                sx={{
                  color: 'white',
                  fontSize: '15px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  display: 'block', // may help in some MUI versions
                  width: '100%',
                }}
                noWrap
              >
                {userEmail}
              </Typography>
            </Box>
            <ChevronDown size={14} color="white" />
          </Box>
        ) : (
          <Box
            sx={{
              mt: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              px: 1,
            }}
          >
            <Avatar
              sx={{
                width: 32,
                height: 32,
                backgroundColor: '#f59e0b',
                fontSize: '0.75rem',
                fontWeight: 600,
              }}
            >
              {authState?.user?.first_name
                ? startCase(authState?.user?.first_name.charAt(0))
                : authState?.user?.email
                  ? authState?.user?.email.charAt(0).toUpperCase()
                  : ''}
            </Avatar>
          </Box>
        )}
      </Box>

      {/* Dropdown */}
      <Popper
        open={open}
        anchorEl={anchorRef.current}
        placement="right-start"
        transition
        disablePortal
        sx={{ zIndex: 1300 }}
      >
        {({ TransitionProps }) => (
          <Grow {...TransitionProps}>
            <Paper sx={{ width: 208, mt: 1, borderRadius: 1 }}>
              <ClickAwayListener onClickAway={handleClose}>
                <MenuList autoFocusItem={open}>
                  <MenuItem sx={menuItemSx}>
                    <ListItemIcon>
                      <User fontSize="small" />
                    </ListItemIcon>
                    View Profile
                  </MenuItem>

                  <Divider />

                  <MenuItem sx={logoutMenuItemSx} onClick={handleLogout}>
                    <ListItemIcon>
                      <LogoutIcon fontSize="small" />
                    </ListItemIcon>
                    Log out
                  </MenuItem>
                </MenuList>
              </ClickAwayListener>
            </Paper>
          </Grow>
        )}
      </Popper>
    </Box>
  );
}
