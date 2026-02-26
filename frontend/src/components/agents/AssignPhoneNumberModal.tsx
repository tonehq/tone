'use client';

import { type TwilioPhoneNumber, getTwilioPhoneNumbers } from '@/services/phoneNumberService';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';
import { X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface AssignPhoneNumberModalProps {
  open: boolean;
  onClose: () => void;
  onAssign: (phoneNumber: string) => void;
  currentPhoneNumber?: string;
}

export default function AssignPhoneNumberModal({
  open,
  onClose,
  onAssign,
  currentPhoneNumber,
}: AssignPhoneNumberModalProps) {
  const [provider, setProvider] = useState('twilio');
  const [phoneNumbers, setPhoneNumbers] = useState<TwilioPhoneNumber[]>([]);
  const [selectedNumber, setSelectedNumber] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchNumbers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getTwilioPhoneNumbers(provider);
      setPhoneNumbers(data);
    } catch {
      setPhoneNumbers([]);
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    if (open) {
      fetchNumbers();
      setSelectedNumber(currentPhoneNumber ?? '');
    }
  }, [open, fetchNumbers, currentPhoneNumber]);

  const handleAssign = () => {
    if (selectedNumber) {
      onAssign(selectedNumber);
      onClose();
    }
  };

  console.log(phoneNumbers, 'phoneNumbers');
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { borderRadius: '8px', maxWidth: '500px' } }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pb: 1,
        }}
      >
        <Typography component="span" variant="h6" sx={{ fontWeight: 600 }}>
          Assign Phone Number
        </Typography>
        <IconButton onClick={onClose} size="small">
          <X size={20} />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 2 }}>
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Service Provider
          </Typography>
          <FormControl size="small" fullWidth>
            <Select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <MenuItem value="twilio">Twilio</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Phone Number
          </Typography>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : phoneNumbers.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No phone numbers found. Please configure your Twilio integration first.
            </Typography>
          ) : (
            <FormControl size="small" fullWidth>
              <Select
                value={selectedNumber}
                onChange={(e) => setSelectedNumber(e.target.value)}
                displayEmpty
                renderValue={(v) => {
                  if (!v) return <span>Select a phone number</span>;
                  return v;
                }}
              >
                {phoneNumbers.map((pn) => (
                  <MenuItem key={pn.phone_number} value={pn.phone_number}>
                    {pn.phone_number}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined" sx={{ borderColor: '#e2e8f0' }}>
          Cancel
        </Button>
        <Button
          onClick={handleAssign}
          variant="contained"
          disabled={!selectedNumber || loading}
          sx={{
            backgroundColor: '#8b5cf6',
            '&:hover': { backgroundColor: '#7c3aed' },
          }}
        >
          Assign
        </Button>
      </DialogActions>
    </Dialog>
  );
}
