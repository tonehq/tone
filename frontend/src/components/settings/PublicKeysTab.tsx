'use client';

import { CustomButton, CustomModal, TextInput } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Switch } from '@/components/ui/switch';
import { type PublicKeyFormData, publicKeySchema } from '@/schemas/settings';
import type { CustomTableColumn } from '@/types/components';
import { formatNow } from '@/utils/date';
import { generateUUID } from '@/utils/helpers';
import { zodResolver } from '@hookform/resolvers/zod';
import { Eye, MoreVertical, Plus, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

export interface PublicKeyRow {
  id: string;
  name: string;
  keyValue: string;
  domains: string;
  abusePrevention: boolean;
  fraudProtection: boolean;
  createdAt: string;
}

function AddPublicKeyModal({
  open,
  onClose,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (data: {
    keyName: string;
    domains: string[];
    abusePrevention: boolean;
    fraudProtection: boolean;
  }) => void;
}) {
  const { control, handleSubmit, reset, formState } = useForm<PublicKeyFormData>({
    resolver: zodResolver(publicKeySchema),
    defaultValues: { keyName: '' },
  });

  const [domainInput, setDomainInput] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [abusePrevention, setAbusePrevention] = useState(false);
  const [fraudProtection, setFraudProtection] = useState(false);

  useEffect(() => {
    if (open) {
      reset({ keyName: '' });
      setDomainInput('');
      setDomains([]);
      setAbusePrevention(false);
      setFraudProtection(false);
    }
  }, [open, reset]);

  const handleAddDomain = () => {
    const d = domainInput.trim();
    if (d && !domains.includes(d)) {
      setDomains([...domains, d]);
      setDomainInput('');
    }
  };

  const onFormSubmit = (data: PublicKeyFormData) => {
    onSave({ keyName: data.keyName.trim(), domains, abusePrevention, fraudProtection });
    reset({ keyName: '' });
    onClose();
  };

  const handleClose = () => {
    reset({ keyName: '' });
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Add Public Key"
      confirmText="Save"
      onConfirm={handleSubmit(onFormSubmit)}
      confirmDisabled={!formState.isValid}
    >
      <div className="space-y-4">
        <TextInput
          name="keyName"
          control={control}
          label="Key Name"
          placeholder="e.g. Staging-Frontend-PubKey (staging frontend public key)"
          isRequired
        />

        <div>
          <p className="mb-1.5 text-sm font-medium">Allowed Domains</p>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <TextInput
                name="domain-input"
                placeholder="e.g. example.com"
                value={domainInput}
                onChange={(e) => setDomainInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddDomain();
                  }
                }}
              />
            </div>
            <CustomButton type="default" onClick={handleAddDomain}>
              + Add
            </CustomButton>
          </div>
          {domains.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {domains.map((d) => (
                <Badge key={d} variant="secondary" className="gap-1 pr-1">
                  {d}
                  <CustomButton
                    type="text"
                    htmlType="button"
                    onClick={() => setDomains(domains.filter((x) => x !== d))}
                    className="size-5 rounded-full p-0 transition-colors hover:bg-muted-foreground/20"
                  >
                    <X className="size-3" />
                  </CustomButton>
                </Badge>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="text-sm font-semibold">Abuse Prevention (Google reCAPTCHA)</p>
          <p className="mb-2 text-sm text-muted-foreground">
            Utilize Google reCAPTCHA to prevent abuse on your applications (forms, widgets, etc.).
            The public key will require reCAPTCHA token to authenticate, so you must also add it on
            frontend. (
            <a href="#" className="text-primary underline">
              See Docs
            </a>
            )
          </p>
          <Switch checked={abusePrevention} onCheckedChange={setAbusePrevention} />
        </div>

        <div>
          <p className="text-sm font-semibold">Fraud Protection</p>
          <p className="mb-2 text-sm text-muted-foreground">
            Once enabled, the system will automatically detect and limit suspicious requests based
            on IP address and destination number.
          </p>
          <Switch checked={fraudProtection} onCheckedChange={setFraudProtection} />
        </div>
      </div>
    </CustomModal>
  );
}

export default function PublicKeysTab() {
  const [publicKeys, setPublicKeys] = useState<PublicKeyRow[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);

  const handleSave = (data: {
    keyName: string;
    domains: string[];
    abusePrevention: boolean;
    fraudProtection: boolean;
  }) => {
    setPublicKeys((prev) => [
      ...prev,
      {
        id: generateUUID(),
        name: data.keyName,
        keyValue: '•••••••••••',
        domains: data.domains.join(', ') || '—',
        abusePrevention: data.abusePrevention,
        fraudProtection: data.fraudProtection,
        createdAt: formatNow(),
      },
    ]);
  };

  const columns: CustomTableColumn<PublicKeyRow>[] = [
    { key: 'name', title: 'Name', dataIndex: 'name' },
    { key: 'keyValue', title: 'Key Value', dataIndex: 'keyValue' },
    { key: 'domains', title: 'Domains', dataIndex: 'domains' },
    {
      key: 'abusePrevention',
      title: 'Abuse Prevention',
      dataIndex: 'abusePrevention',
      render: (value) => <span className="text-sm">{value ? 'On' : 'Off'}</span>,
    },
    {
      key: 'fraudProtection',
      title: 'Fraud Protection',
      dataIndex: 'fraudProtection',
      render: (value) => <span className="text-sm">{value ? 'On' : 'Off'}</span>,
    },
    { key: 'createdAt', title: 'Created at', dataIndex: 'createdAt' },
    {
      key: 'actions',
      title: '',
      width: 'w-14',
      render: () => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <CustomButton
              type="text"
              size="icon-xs"
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <MoreVertical className="size-4" />
            </CustomButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="size-4" />
              Reveal key
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive">
              <Trash2 className="size-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <CustomButton
          type="primary"
          icon={<Plus size={18} />}
          onClick={() => setAddModalOpen(true)}
        >
          Add Public Key
        </CustomButton>
      </div>

      <CustomTable columns={columns} dataSource={publicKeys} rowKey="id" />

      <AddPublicKeyModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSave={handleSave}
      />
    </div>
  );
}
