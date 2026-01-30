import {
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
} from '@mui/material';
import * as React from 'react';

import { authAtom, getCurrentUserAtom, logoutAtom } from '@/atoms/AuthAtom';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAtom, useSetAtom } from 'jotai';
import { startCase } from 'lodash';
import { User } from 'lucide-react';

export default function ProfileMenu() {
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

  console.log(authState, 'authState');

  const handleToggle = () => setOpen((prev) => !prev);

  const handleClose = (event: Event | React.SyntheticEvent) => {
    if (anchorRef.current?.contains(event.target as HTMLElement)) return;
    setOpen(false);
  };

  const userEmail = authState?.user?.email;

  const getEllipsedEmail = (email: string, maxLength = 18) => {
    if (email.length <= maxLength) return email;
    const parts = email.split('@');
    if (parts.length !== 2) return email;
    const [name, domain] = parts;
    const visibleChars = 6;
    if (name.length + domain.length + 1 <= maxLength) return email;
    if (name.length <= visibleChars) {
      return `${name}@...${domain.slice(-(maxLength - name.length - 4))}`;
    }
    const ellipsed = `${name.slice(0, visibleChars)}...` + `@${domain}`;
    if (ellipsed.length > maxLength) {
      const domainPart = domain.length > 8 ? `...${domain.slice(-8)}` : domain;
      return `${name.slice(0, visibleChars)}...` + `@${domainPart}`;
    }
    return ellipsed;
  };

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
          bgcolor: 'grey.100',
          borderRadius: 1,
          px: 1.5,
          py: 1.5,
          gap: 1,
          width: 208,
          cursor: 'pointer',
          textTransform: 'none',
          transition: 'background 0.15s',
          '&:hover': {
            bgcolor: 'grey.200',
          },
          userSelect: 'none',
        }}
      >
        <Box
          sx={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            border: '1px solid #1d4ed8',
            color: '#1d4ed8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          {authState?.user?.first_name
            ? startCase(authState?.user?.first_name.charAt(0))
            : authState?.user?.email
              ? authState?.user?.email.charAt(0).toUpperCase()
              : ''}
        </Box>
        <Typography
          fontSize={14}
          sx={{
            maxWidth: 120,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: 'block',
            color: 'GrayText',
          }}
          title={userEmail}
        >
          {getEllipsedEmail(userEmail ?? '', 18)}
        </Typography>
        <KeyboardArrowDownIcon fontSize="small" sx={{ color: 'GrayText' }} />
      </Box>

      {/* Dropdown */}
      <Popper
        open={open}
        anchorEl={anchorRef.current}
        placement="bottom-end"
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
