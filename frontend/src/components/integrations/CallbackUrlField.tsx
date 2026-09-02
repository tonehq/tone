'use client';

import { CustomButton } from '@/components/shared';
import { BACKEND_URL } from '@/constants';
import { showToast } from '@/utils/toast';
import { Check, Copy, Link2 } from 'lucide-react';
import { useState } from 'react';

interface CallbackUrlFieldProps {
  /** Current value of the slug field — used to build the per-integration URL.
   * Updated reactively via ``useWatch`` so the URL stays in sync with typing. */
  slug: string;
}

export default function CallbackUrlField({ slug }: CallbackUrlFieldProps) {
  const [copied, setCopied] = useState(false);

  // BACKEND_URL already includes the ``/api/v1`` prefix, so we just append
  // ``/oauth/{slug}/callback``. Falls back to a placeholder slug when the
  // admin hasn't typed one yet so the URL shape is still demonstrable.
  const displaySlug = slug?.trim() || '{slug}';
  const callbackUrl = `${BACKEND_URL}/oauth/${displaySlug}/callback`;
  const canCopy = Boolean(slug?.trim());

  const handleCopy = async () => {
    if (!canCopy) return;
    try {
      await navigator.clipboard.writeText(callbackUrl);
      setCopied(true);
      showToast.success('Callback URL copied');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      showToast.error('Could not access the clipboard');
    }
  };

  return (
    <div className="rounded-md border border-violet-200/60 bg-violet-50/40 p-3 dark:border-violet-500/20 dark:bg-violet-500/[0.06]">
      <div className="flex items-center gap-2">
        <Link2 size={13} className="text-violet-500" />
        <p className="text-[12.5px] font-semibold text-foreground">Callback URL</p>
      </div>
      <p className="mt-0.5 text-[11.5px] text-muted-foreground">
        Add this exact URL to your provider&apos;s OAuth app as an allowed redirect URL.
      </p>
      <div className="mt-2.5 flex items-stretch gap-1.5">
        <code className="flex-1 truncate rounded-md border border-border/60 bg-background px-2.5 py-1.5 font-mono text-[11.5px] text-foreground">
          {callbackUrl}
        </code>
        <CustomButton
          type="default"
          size="sm"
          onClick={handleCopy}
          disabled={!canCopy}
          icon={copied ? <Check size={12} /> : <Copy size={12} />}
          aria-label="Copy callback URL"
        >
          {copied ? 'Copied' : 'Copy'}
        </CustomButton>
      </div>
    </div>
  );
}
