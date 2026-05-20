'use client';

import { CustomModal, PhoneNumberDisplay, SelectInput } from '@/components/shared';
import ToneLoader from '@/components/shared/ToneLoader';
import { Checkbox } from '@/components/ui/checkbox';
import { getChannelsByType } from '@/services/channelService';
import { type TwilioPhoneNumber, getTwilioPhoneNumbers } from '@/services/phoneNumberService';
import { cn } from '@/utils/cn';
import { useCallback, useEffect, useState } from 'react';

const PROVIDER_OPTIONS = [
  { value: 'twilio', label: 'Twilio' },
  { value: 'exotel', label: 'Exotel' },
  { value: 'telnyx', label: 'Telnyx' },
];

interface ChannelOption {
  id: number;
  name: string;
}

interface PhoneNumberEntry {
  type: string;
  no: string;
}

interface AssignPhoneNumberModalProps {
  open: boolean;
  onClose: () => void;
  onAssign: (phoneNumbers: PhoneNumberEntry[]) => Promise<void>;
  currentPhoneNumbers?: PhoneNumberEntry[];
  agentId?: number;
  channelId?: number | null;
}

export default function AssignPhoneNumberModal({
  open,
  onClose,
  onAssign,
  currentPhoneNumbers = [],
  agentId,
  channelId: initialChannelId,
}: AssignPhoneNumberModalProps) {
  const [provider, setProvider] = useState('twilio');
  const [channels, setChannels] = useState<ChannelOption[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<number | null>(
    initialChannelId ?? null,
  );
  const [loadingChannels, setLoadingChannels] = useState(false);
  const [phoneNumbers, setPhoneNumbers] = useState<TwilioPhoneNumber[]>([]);
  const [selectedNos, setSelectedNos] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const myAssignedNos = currentPhoneNumbers.map((p) => p.no);

  // Sync initial channelId prop when modal opens
  useEffect(() => {
    if (open && initialChannelId) {
      setSelectedChannelId(initialChannelId);
    }
  }, [open, initialChannelId]);

  // Fetch channels when provider changes
  const fetchChannels = useCallback(
    async (type: string) => {
      setLoadingChannels(true);
      try {
        const data = await getChannelsByType(type);
        const opts = data.map((c: any) => ({ id: c.id, name: c.name }));
        setChannels(opts);
        // Auto-select if only one channel or if initialChannelId matches
        if (opts.length === 1) {
          setSelectedChannelId(opts[0].id);
        } else if (initialChannelId && opts.some((c: ChannelOption) => c.id === initialChannelId)) {
          setSelectedChannelId(initialChannelId);
        }
      } catch {
        setChannels([]);
      } finally {
        setLoadingChannels(false);
      }
    },
    [initialChannelId],
  );

  useEffect(() => {
    if (open) {
      fetchChannels(provider);
    }
  }, [open, provider, fetchChannels]);

  // Fetch phone numbers when channel is selected
  const fetchNumbers = useCallback(async () => {
    if (!selectedChannelId) {
      setPhoneNumbers([]);
      return;
    }
    setLoading(true);
    try {
      const data = await getTwilioPhoneNumbers(provider, agentId, selectedChannelId);
      setPhoneNumbers(data);
    } catch {
      setPhoneNumbers([]);
    } finally {
      setLoading(false);
    }
  }, [provider, agentId, selectedChannelId]);

  useEffect(() => {
    if (open && selectedChannelId) {
      fetchNumbers();
      setSelectedNos(currentPhoneNumbers.map((p) => p.no));
    }
  }, [open, selectedChannelId, fetchNumbers, currentPhoneNumbers]);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setSelectedNos(currentPhoneNumbers.map((p) => p.no));
    }
  }, [open, currentPhoneNumbers]);

  const handleProviderChange = (value: string) => {
    setProvider(value);
    setSelectedChannelId(null);
    setChannels([]);
    setPhoneNumbers([]);
    setSelectedNos(currentPhoneNumbers.map((p) => p.no));
  };

  const handleChannelChange = (value: string) => {
    setSelectedChannelId(value ? Number(value) : null);
    setPhoneNumbers([]);
    setSelectedNos(currentPhoneNumbers.map((p) => p.no));
  };

  const toggleNumber = (no: string) => {
    if (myAssignedNos.includes(no)) return;
    setSelectedNos((prev) => (prev.includes(no) ? prev.filter((n) => n !== no) : [...prev, no]));
  };

  const handleAssign = async () => {
    const entries: PhoneNumberEntry[] = selectedNos
      .filter((no) => !myAssignedNos.includes(no))
      .map((no) => ({ type: provider, no }));
    setAssigning(true);
    try {
      await onAssign(entries);
      onClose();
    } finally {
      setAssigning(false);
    }
  };

  const newSelections = selectedNos.filter((no) => !myAssignedNos.includes(no));

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign Phone Numbers"
      confirmText="Assign"
      confirmDisabled={newSelections.length === 0 || loading}
      confirmLoading={assigning}
      onConfirm={handleAssign}
    >
      <div className="space-y-4">
        <SelectInput
          name="provider"
          label="Service Provider"
          value={provider}
          onValueChange={handleProviderChange}
          options={PROVIDER_OPTIONS}
        />

        <SelectInput
          name="channel"
          label="Channel"
          value={selectedChannelId?.toString() ?? ''}
          onValueChange={handleChannelChange}
          options={channels.map((c) => ({ value: c.id.toString(), label: c.name }))}
          placeholder={
            loadingChannels
              ? 'Loading channels...'
              : channels.length === 0
                ? 'No channels found'
                : 'Select a channel'
          }
        />

        <div>
          <label className="mb-1 block text-sm font-semibold text-foreground">Phone Numbers</label>
          {!selectedChannelId ? (
            <p className="text-sm text-muted-foreground">
              Select a channel to see available numbers.
            </p>
          ) : loading ? (
            <div className="flex justify-center py-4">
              <ToneLoader size="sm" />
            </div>
          ) : phoneNumbers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No phone numbers found. Please configure your integration first.
            </p>
          ) : (
            <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border border-border p-2">
              {phoneNumbers.map((pn) => {
                const isAssigned = myAssignedNos.includes(pn.phone_number);
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
                    <PhoneNumberDisplay
                      phoneNumber={pn.phone_number}
                      flagSize="sm"
                      className="flex-1"
                    />
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
