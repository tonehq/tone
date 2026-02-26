'use client';

import { CustomModal, SelectInput } from '@/components/shared';
import { type TwilioPhoneNumber, getTwilioPhoneNumbers } from '@/services/phoneNumberService';
import { Loader2 } from 'lucide-react';
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

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign Phone Number"
      confirmText="Assign"
      confirmDisabled={!selectedNumber || loading}
      onConfirm={handleAssign}
    >
      <div className="space-y-4">
        <SelectInput
          name="provider"
          label="Service Provider"
          value={provider}
          onValueChange={setProvider}
          options={[{ value: 'twilio', label: 'Twilio' }]}
        />

        <div>
          <label className="mb-1 block text-sm font-semibold text-foreground">Phone Number</label>
          {loading ? (
            <div className="flex justify-center py-2">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : phoneNumbers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No phone numbers found. Please configure your Twilio integration first.
            </p>
          ) : (
            <SelectInput
              name="phoneNumber"
              value={selectedNumber}
              onValueChange={setSelectedNumber}
              placeholder="Select a phone number"
              options={phoneNumbers.map((pn) => ({
                value: pn.phone_number,
                label: pn.phone_number,
              }))}
            />
          )}
        </div>
      </div>
    </CustomModal>
  );
}
