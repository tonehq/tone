'use client';

import { CustomButton } from '@/components/shared';
import type { IntegrationRow } from '@/types/integration';
import { Check, Copy, Eye, EyeOff, Key, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface ApiKeyCredentialRowProps {
  row: IntegrationRow;
  onEdit: (row: IntegrationRow) => void;
  onDelete: (id: number) => void;
}

export default function ApiKeyCredentialRow({ row, onEdit, onDelete }: ApiKeyCredentialRowProps) {
  const [tokenVisible, setTokenVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(row.auth_token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border/40 bg-muted/30 px-3 py-2 transition-colors hover:bg-muted/50">
      <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-500/15">
        <Key size={10} className="text-amber-600 dark:text-amber-400" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-medium text-foreground">{row.name}</p>
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <span className="max-w-[120px] truncate font-mono">{row.account_sid}</span>
          <span className="opacity-30">·</span>
          <span className="font-mono">{tokenVisible ? row.auth_token : '••••••'}</span>
          <button
            type="button"
            onClick={() => setTokenVisible(!tokenVisible)}
            className="ml-0.5 text-muted-foreground/60 transition-colors hover:text-foreground"
            aria-label={tokenVisible ? 'Hide token' : 'Show token'}
          >
            {tokenVisible ? <Eye size={9} /> : <EyeOff size={9} />}
          </button>
          <button
            type="button"
            onClick={handleCopy}
            className="text-muted-foreground/60 transition-colors hover:text-foreground"
            aria-label="Copy token"
          >
            {copied ? <Check size={9} className="text-emerald-500" /> : <Copy size={9} />}
          </button>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-0.5">
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={() => onEdit(row)}
          className="text-muted-foreground/50 transition-colors hover:text-foreground"
          aria-label="Edit"
        >
          <Pencil size={11} />
        </CustomButton>
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={() => onDelete(row.id)}
          className="text-muted-foreground/50 transition-colors hover:text-destructive"
          aria-label="Delete"
        >
          <Trash2 size={11} />
        </CustomButton>
      </div>
    </div>
  );
}
