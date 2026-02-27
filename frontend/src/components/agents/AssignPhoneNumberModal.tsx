'use client';

import { CustomModal, SelectInput } from '@/components/shared';
import { Checkbox } from '@/components/ui/checkbox';
import { type TwilioPhoneNumber, getTwilioPhoneNumbers } from '@/services/phoneNumberService';
import { cn } from '@/utils/cn';
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

  const assignedNos = currentPhoneNumbers.map((p) => p.no);

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
    if (assignedNos.includes(no)) return;
    setSelectedNos((prev) => (prev.includes(no) ? prev.filter((n) => n !== no) : [...prev, no]));
  };

  const handleAssign = () => {
    const entries: PhoneNumberEntry[] = selectedNos
      .filter((no) => !assignedNos.includes(no))
      .map((no) => ({ type: provider, no }));
    onAssign(entries);
    onClose();
  };

  const newSelections = selectedNos.filter((no) => !assignedNos.includes(no));

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign Phone Numbers"
      confirmText="Assign"
      confirmDisabled={newSelections.length === 0 || loading}
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
              {phoneNumbers.map((pn) => {
                const isAssigned = assignedNos.includes(pn.phone_number);
                return (
                  <label
                    key={pn.phone_number}
                    className={cn(
                      'flex items-center gap-2 rounded px-2 py-1.5 text-sm',
                      isAssigned
                        ? 'cursor-not-allowed opacity-60'
                        : 'cursor-pointer hover:bg-accent',
                    )}
                  >
                    <Checkbox
                      checked={selectedNos.includes(pn.phone_number)}
                      onCheckedChange={() => toggleNumber(pn.phone_number)}
                      disabled={isAssigned}
                    />
                    <span className="flex-1">{pn.phone_number}</span>
                    {isAssigned && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        Assigned
                      </span>
                    )}
                  </label>
                );
              })}
            </div>
          )}
          {newSelections.length > 0 && (
            <p className="mt-1 text-xs text-muted-foreground">
              {newSelections.length} new number{newSelections.length > 1 ? 's' : ''} selected
            </p>
          )}
        </div>
      </div>
    </CustomModal>
  );
}
