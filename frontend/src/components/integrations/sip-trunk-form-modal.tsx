'use client';

import {
  AppLoader,
  CheckboxField,
  CustomButton,
  CustomModal,
  SelectInput,
  TextInput,
} from '@/components/shared';
import { useSipTrunk } from '@/lib/api/sipTrunks';
import type {
  SipAuthMode,
  SipGateway,
  SipMediaEncryption,
  SipTrunk,
  SipTrunkPayload,
  SipTransport,
} from '@/types/sipTrunk';
import { Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

const TRANSPORT_OPTIONS = [
  { label: 'UDP', value: 'udp' },
  { label: 'TCP', value: 'tcp' },
  { label: 'TLS', value: 'tls' },
];

const AUTH_MODE_OPTIONS = [
  { label: 'IP allowlist', value: 'ip_acl' },
  { label: 'Digest (username / password)', value: 'digest' },
];

const MEDIA_ENCRYPTION_OPTIONS = [
  { label: 'None (RTP)', value: 'none' },
  { label: 'SRTP', value: 'srtp' },
];

const DEFAULT_PORTS: Record<SipTransport, number> = { udp: 5060, tcp: 5060, tls: 5061 };

const newGateway = (priority: number): SipGateway => ({
  host: '',
  port: 5060,
  transport: 'udp',
  inbound_enabled: true,
  outbound_enabled: true,
  priority,
});

interface SipTrunkFormData {
  name: string;
  tech_prefix: string;
  auth_username: string;
  auth_password: string;
  register_server: string;
}

const emptyValues = (): SipTrunkFormData => ({
  name: '',
  tech_prefix: '',
  auth_username: '',
  auth_password: '',
  register_server: '',
});

interface SipTrunkFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: SipTrunkPayload, trunkId?: string) => Promise<void>;
  editTrunk?: SipTrunk | null;
  carriers: string[];
}

export default function SipTrunkFormModal({
  open,
  onClose,
  onSubmit,
  editTrunk,
  carriers,
}: SipTrunkFormModalProps) {
  const isEdit = Boolean(editTrunk);
  const { control, handleSubmit, reset } = useForm<SipTrunkFormData>({
    defaultValues: emptyValues(),
    mode: 'onChange',
  });

  const [carrier, setCarrier] = useState('telnyx');
  const [authMode, setAuthMode] = useState<SipAuthMode>('ip_acl');
  const [mediaEncryption, setMediaEncryption] = useState<SipMediaEncryption>('none');
  const [gateways, setGateways] = useState<SipGateway[]>([newGateway(1)]);
  const [inboundEnabled, setInboundEnabled] = useState(true);
  const [outboundEnabled, setOutboundEnabled] = useState(true);
  const [leadingPlus, setLeadingPlus] = useState(true);
  const [e164Check, setE164Check] = useState(true);
  const [diversionHeader, setDiversionHeader] = useState(false);
  const [transferEnabled, setTransferEnabled] = useState(true);
  const [registerEnabled, setRegisterEnabled] = useState(false);
  const [saving, setSaving] = useState(false);

  const { data: fullTrunk, isLoading: hydrating } = useSipTrunk(
    open && editTrunk ? editTrunk.id : null,
    true,
  );

  useEffect(() => {
    if (!open) return;
    if (!editTrunk) {
      reset(emptyValues());
      setCarrier(carriers[0] ?? 'telnyx');
      setAuthMode('ip_acl');
      setMediaEncryption('none');
      setGateways([newGateway(1)]);
      setInboundEnabled(true);
      setOutboundEnabled(true);
      setLeadingPlus(true);
      setE164Check(true);
      setDiversionHeader(false);
      setTransferEnabled(true);
      setRegisterEnabled(false);
      return;
    }

    const full = fullTrunk;
    if (!full) return;

    reset({
      name: full.name,
      tech_prefix: full.tech_prefix ?? '',
      auth_username: full.auth?.auth_username ?? '',
      auth_password: full.auth?.auth_password ?? '',
      register_server: full.auth?.register_server ?? '',
    });
    setCarrier(full.carrier);
    setAuthMode(full.auth_mode);
    setMediaEncryption(full.media_encryption);
    setGateways(full.gateways.length ? full.gateways : [newGateway(1)]);
    setInboundEnabled(full.inbound_enabled);
    setOutboundEnabled(full.outbound_enabled);
    setLeadingPlus(full.outbound_leading_plus_enabled);
    setE164Check(full.number_e164_check_enabled);
    setDiversionHeader(full.sip_diversion_header);
    setTransferEnabled(full.transfer_enabled);
    setRegisterEnabled(full.register_enabled);
  }, [open, editTrunk, fullTrunk, carriers, reset]);

  const values = useWatch({ control });

  const updateGateway = useCallback((index: number, patch: Partial<SipGateway>) => {
    setGateways((prev) =>
      prev.map((gateway, i) => (i === index ? { ...gateway, ...patch } : gateway)),
    );
  }, []);

  const addGateway = useCallback(() => {
    setGateways((prev) => [...prev, newGateway(prev.length + 1)]);
  }, []);

  const removeGateway = useCallback((index: number) => {
    setGateways((prev) => (prev.length === 1 ? prev : prev.filter((_gateway, i) => i !== index)));
  }, []);

  const hasGateway = gateways.some((gateway) => gateway.host.trim().length > 0);
  const digestComplete =
    authMode !== 'digest' ||
    ((values?.auth_username ?? '').trim().length > 0 &&
      (values?.auth_password ?? '').trim().length > 0);
  const canSave = (values?.name ?? '').trim().length > 0 && hasGateway && digestComplete;

  const onFormSubmit = async (data: SipTrunkFormData) => {
    setSaving(true);
    try {
      const payload: SipTrunkPayload = {
        name: data.name.trim(),
        carrier,
        gateways: gateways
          .filter((gateway) => gateway.host.trim().length > 0)
          .map((gateway, index) => ({
            ...gateway,
            host: gateway.host.trim(),
            priority: index + 1,
          })),
        inbound_enabled: inboundEnabled,
        outbound_enabled: outboundEnabled,
        auth_mode: authMode,
        media_encryption: mediaEncryption,
        tech_prefix: data.tech_prefix.trim() || null,
        outbound_leading_plus_enabled: leadingPlus,
        number_e164_check_enabled: e164Check,
        sip_diversion_header: diversionHeader,
        transfer_enabled: transferEnabled,
        register_enabled: registerEnabled,
        auth: {
          auth_username: data.auth_username.trim(),
          auth_password: data.auth_password.trim(),
          register_server: data.register_server.trim(),
        },
      };
      await onSubmit(payload, editTrunk?.id);
      reset(emptyValues());
      onClose();
    } catch {
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    reset(emptyValues());
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title={isEdit ? 'Edit SIP trunk' : 'Add SIP trunk'}
      confirmText={saving ? 'Saving...' : 'Save'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!canSave || hydrating}
    >
      {hydrating ? (
        <AppLoader className="min-h-[320px]" />
      ) : (
        <div className="space-y-5">
          <TextInput
            name="name"
            control={control}
            label="Name"
            placeholder="e.g. Telnyx production trunk"
            rules={{ required: 'Name is required' }}
            isRequired
            disabled={saving}
          />

          <SelectInput
            name="carrier"
            label="Carrier"
            options={carriers.map((value) => ({
              label: value === 'generic' ? 'Generic / other carrier' : 'Telnyx',
              value,
            }))}
            value={carrier}
            onValueChange={(value) => setCarrier(value)}
            disabled={saving || isEdit}
            helperText={
              isEdit ? 'Carrier cannot be changed after the trunk is created.' : undefined
            }
          />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">Gateways</span>
              <CustomButton type="text" onClick={addGateway} disabled={saving}>
                <Plus className="size-3.5" />
                Add gateway
              </CustomButton>
            </div>

            {gateways.map((gateway, index) => (
              <div
                key={`gateway-${index}`}
                className="space-y-3 rounded-xl border border-border/70 bg-muted/20 p-3"
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <TextInput
                      name={`gateway-host-${index}`}
                      label="Host"
                      placeholder="sip.telnyx.com or 192.0.2.10/32"
                      value={gateway.host}
                      onChange={(event) => updateGateway(index, { host: event.target.value })}
                      disabled={saving}
                    />
                  </div>
                  <div className="w-24">
                    <TextInput
                      name={`gateway-port-${index}`}
                      label="Port"
                      type="number"
                      value={String(gateway.port)}
                      onChange={(event) =>
                        updateGateway(index, { port: Number(event.target.value) || 0 })
                      }
                      disabled={saving}
                    />
                  </div>
                  <div className="w-28">
                    <SelectInput
                      name={`gateway-transport-${index}`}
                      label="Transport"
                      options={TRANSPORT_OPTIONS}
                      value={gateway.transport}
                      onValueChange={(value) =>
                        updateGateway(index, {
                          transport: value as SipTransport,
                          port: DEFAULT_PORTS[value as SipTransport],
                        })
                      }
                      disabled={saving}
                    />
                  </div>
                  <CustomButton
                    type="text"
                    onClick={() => removeGateway(index)}
                    disabled={saving || gateways.length === 1}
                    className="mt-6"
                  >
                    <Trash2 className="size-3.5" />
                  </CustomButton>
                </div>

                <div className="flex flex-wrap gap-4">
                  <CheckboxField
                    id={`gateway-inbound-${index}`}
                    label="Accepts inbound"
                    checked={gateway.inbound_enabled}
                    onCheckedChange={(checked) =>
                      updateGateway(index, { inbound_enabled: Boolean(checked) })
                    }
                    disabled={saving}
                  />
                  <CheckboxField
                    id={`gateway-outbound-${index}`}
                    label="Used for outbound"
                    checked={gateway.outbound_enabled}
                    onCheckedChange={(checked) =>
                      updateGateway(index, { outbound_enabled: Boolean(checked) })
                    }
                    disabled={saving}
                  />
                </div>
              </div>
            ))}
          </div>

          <SelectInput
            name="auth_mode"
            label="Authentication"
            options={AUTH_MODE_OPTIONS}
            value={authMode}
            onValueChange={(value) => setAuthMode(value as SipAuthMode)}
            disabled={saving}
            helperText={
              authMode === 'ip_acl'
                ? 'Inbound INVITEs are accepted only from the gateway hosts above.'
                : 'The carrier authenticates with these credentials on every INVITE.'
            }
          />

          {authMode === 'digest' && (
            <div className="space-y-4">
              <TextInput
                name="auth_username"
                control={control}
                label="Auth username"
                placeholder="Enter SIP username"
                rules={{ required: 'Auth username is required for digest' }}
                isRequired
                disabled={saving}
              />
              <TextInput
                name="auth_password"
                control={control}
                label="Auth password"
                type="password"
                placeholder="Enter SIP password"
                rules={{ required: 'Auth password is required for digest' }}
                isRequired
                disabled={saving}
              />
              <CheckboxField
                id="register_enabled"
                label="Register with the carrier"
                checked={registerEnabled}
                onCheckedChange={(checked) => setRegisterEnabled(Boolean(checked))}
                disabled={saving}
              />
              {registerEnabled && (
                <TextInput
                  name="register_server"
                  control={control}
                  label="Registrar"
                  placeholder="sip.telnyx.com"
                  disabled={saving}
                />
              )}
            </div>
          )}

          <SelectInput
            name="media_encryption"
            label="Media encryption"
            options={MEDIA_ENCRYPTION_OPTIONS}
            value={mediaEncryption}
            onValueChange={(value) => setMediaEncryption(value as SipMediaEncryption)}
            disabled={saving}
          />

          <TextInput
            name="tech_prefix"
            control={control}
            label="Tech prefix"
            placeholder="Optional dialing prefix"
            helperText="Prepended to every dialled number on this trunk."
            disabled={saving}
          />

          <div className="grid grid-cols-2 gap-3">
            <CheckboxField
              id="inbound_enabled"
              label="Accept inbound calls"
              checked={inboundEnabled}
              onCheckedChange={(checked) => setInboundEnabled(Boolean(checked))}
              disabled={saving}
            />
            <CheckboxField
              id="outbound_enabled"
              label="Allow outbound calls"
              checked={outboundEnabled}
              onCheckedChange={(checked) => setOutboundEnabled(Boolean(checked))}
              disabled={saving}
            />
            <CheckboxField
              id="outbound_leading_plus_enabled"
              label="Keep leading +"
              checked={leadingPlus}
              onCheckedChange={(checked) => setLeadingPlus(Boolean(checked))}
              disabled={saving}
            />
            <CheckboxField
              id="number_e164_check_enabled"
              label="Enforce E.164"
              checked={e164Check}
              onCheckedChange={(checked) => setE164Check(Boolean(checked))}
              disabled={saving}
            />
            <CheckboxField
              id="sip_diversion_header"
              label="Send Diversion header"
              checked={diversionHeader}
              onCheckedChange={(checked) => setDiversionHeader(Boolean(checked))}
              disabled={saving}
            />
            <CheckboxField
              id="transfer_enabled"
              label="Allow REFER transfer"
              checked={transferEnabled}
              onCheckedChange={(checked) => setTransferEnabled(Boolean(checked))}
              disabled={saving}
            />
          </div>
        </div>
      )}
    </CustomModal>
  );
}
