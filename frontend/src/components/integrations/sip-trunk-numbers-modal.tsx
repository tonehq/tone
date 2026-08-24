'use client';

import { AppLoader, CustomButton, CustomModal, SelectInput, TextInput } from '@/components/shared';
import {
  useAttachSipNumber,
  useDetachSipNumber,
  useSipCarrierNumbers,
  useSipTrunkPhoneNumbers,
} from '@/lib/api/sipTrunks';
import type { SipTrunk } from '@/types/sipTrunk';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { Phone, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

interface SipTrunkNumbersModalProps {
  open: boolean;
  onClose: () => void;
  trunk: SipTrunk | null;
}

export default function SipTrunkNumbersModal({ open, onClose, trunk }: SipTrunkNumbersModalProps) {
  const trunkId = open && trunk ? trunk.id : null;
  const { data: attached, isLoading } = useSipTrunkPhoneNumbers(trunkId);
  const { data: carrierNumbers } = useSipCarrierNumbers(trunkId);
  const attachNumber = useAttachSipNumber();
  const detachNumber = useDetachSipNumber();

  const [selected, setSelected] = useState('');
  const [manualNumber, setManualNumber] = useState('');
  const [busy, setBusy] = useState(false);

  const available = useMemo(() => {
    const taken = new Set((attached ?? []).map((row) => row.number));
    return (carrierNumbers ?? []).filter((row) => !taken.has(row.number));
  }, [carrierNumbers, attached]);

  const numberToAttach = (selected || manualNumber).trim();

  const handleAttach = async () => {
    if (!trunk || !numberToAttach) return;
    setBusy(true);
    try {
      await attachNumber.mutateAsync({ trunkId: trunk.id, number: numberToAttach });
      showToast.success(`${numberToAttach} attached to ${trunk.name}`);
      setSelected('');
      setManualNumber('');
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleDetach = async (number: string) => {
    if (!trunk) return;
    setBusy(true);
    try {
      await detachNumber.mutateAsync({ trunkId: trunk.id, number });
      showToast.success(`${number} detached`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={trunk ? `Numbers — ${trunk.name}` : 'Numbers'}
      confirmText="Done"
      onConfirm={onClose}
    >
      {isLoading ? (
        <AppLoader className="min-h-55" />
      ) : (
        <div className="space-y-5">
          <div className="space-y-2">
            {(attached ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/70 bg-muted/20 px-4 py-5 text-center text-sm text-muted-foreground">
                No numbers attached yet. SIP routing activates once this trunk has at least one
                number.
              </div>
            ) : (
              (attached ?? []).map((row) => (
                <div
                  key={row.id}
                  className="flex items-center gap-3 rounded-xl border border-border/70 bg-card px-3 py-2.5"
                >
                  <Phone className="size-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-mono text-sm text-foreground">{row.number}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {row.assigned_to
                        ? `Agent: ${row.assigned_to.agent_name}`
                        : 'Not assigned to an agent yet'}
                    </p>
                  </div>
                  <CustomButton
                    type="text"
                    onClick={() => handleDetach(row.number)}
                    disabled={busy}
                  >
                    <Trash2 className="size-3.5" />
                  </CustomButton>
                </div>
              ))
            )}
          </div>

          <div className="space-y-3 rounded-xl border border-border/70 bg-muted/20 p-3">
            {available.length > 0 && (
              <SelectInput
                name="carrier-number"
                label={`Available on ${trunk?.carrier ?? 'carrier'}`}
                options={available.map((row) => ({
                  label: row.label ? `${row.number} — ${row.label}` : row.number,
                  value: row.number,
                }))}
                value={selected}
                onValueChange={(value) => {
                  setSelected(value);
                  setManualNumber('');
                }}
                disabled={busy}
              />
            )}

            <TextInput
              name="manual-number"
              label="Or enter a number"
              placeholder="+14155550123"
              value={manualNumber}
              onChange={(event) => {
                setManualNumber(event.target.value);
                setSelected('');
              }}
              disabled={busy}
              helperText="Attaching moves the number onto this trunk on the carrier side."
            />

            <CustomButton
              onClick={handleAttach}
              disabled={busy || !numberToAttach}
              loading={busy}
              fullWidth
            >
              Attach number
            </CustomButton>
          </div>
        </div>
      )}
    </CustomModal>
  );
}
