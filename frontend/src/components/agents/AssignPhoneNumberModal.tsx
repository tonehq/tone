'use client';

import { CustomModal, SelectInput } from '@/components/shared';
import { Checkbox } from '@/components/ui/checkbox';
import { type TwilioPhoneNumber, getTwilioPhoneNumbers } from '@/services/phoneNumberService';
import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface PhoneNumberEntry {
  type: string;
  no: string;
}

interface AssignPhoneNumberModalProps {
  open: boolean;
  onClose: () => void;
  onAssign: (phoneNumbers: PhoneNumberEntry[]) => void;
  currentPhoneNumbers?: PhoneNumberEntry[];
}

export default function AssignPhoneNumberModal({
  open,
  onClose,
  onAssign,
  currentPhoneNumbers = [],
}: AssignPhoneNumberModalProps) {
  const [provider, setProvider] = useState('twilio');
  const [phoneNumbers, setPhoneNumbers] = useState<TwilioPhoneNumber[]>([]);
  const [selectedNos, setSelectedNos] = useState<string[]>([]);
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
      setSelectedNos(currentPhoneNumbers.map((p) => p.no));
    }
  }, [open, fetchNumbers, currentPhoneNumbers]);

  const toggleNumber = (no: string) => {
    setSelectedNos((prev) =>
      prev.includes(no) ? prev.filter((n) => n !== no) : [...prev, no],
    );
  };

  const handleAssign = () => {
    const entries: PhoneNumberEntry[] = selectedNos.map((no) => ({ type: provider, no }));
    onAssign(entries);
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign Phone Numbers"
      confirmText="Assign"
      confirmDisabled={selectedNos.length === 0 || loading}
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
          <label className="mb-1 block text-sm font-semibold text-foreground">Phone Numbers</label>
          {loading ? (
            <div className="flex justify-center py-2">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : phoneNumbers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No phone numbers found. Please configure your Twilio integration first.
            </p>
          ) : (
            <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border border-border p-2">
              {phoneNumbers.map((pn) => (
                <label
                  key={pn.phone_number}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-accent"
                >
                  <Checkbox
                    checked={selectedNos.includes(pn.phone_number)}
                    onCheckedChange={() => toggleNumber(pn.phone_number)}
                  />
                  {pn.phone_number}
                </label>
              ))}
            </div>
          )}
          {selectedNos.length > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {selectedNos.length} number{selectedNos.length > 1 ? 's' : ''} selected
            </p>
          )}
        </div>
      </div>
    </CustomModal>
  );
}
