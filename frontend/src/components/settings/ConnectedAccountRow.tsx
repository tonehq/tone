'use client';

import { CustomButton } from '@/components/shared';
import type { OAuthConnection } from '@/types/oauth';
import { formatDate } from '@/utils/date';
import { Trash2, UserCircle } from 'lucide-react';

interface ConnectedAccountRowProps {
  connection: OAuthConnection;
  onDisconnect: (id: number) => void;
  disconnecting: boolean;
}

export default function ConnectedAccountRow({
  connection,
  onDisconnect,
  disconnecting,
}: ConnectedAccountRowProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border/40 bg-muted/30 px-3 py-2 transition-colors hover:bg-muted/50">
      <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-500/15">
        <UserCircle size={12} className="text-emerald-600 dark:text-emerald-400" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-medium text-foreground">
          {connection.user_email ?? 'Connected account'}
        </p>
        {connection.created_at && (
          <p className="text-[10px] text-muted-foreground">{formatDate(connection.created_at)}</p>
        )}
      </div>
      <CustomButton
        type="text"
        size="icon-xs"
        onClick={() => onDisconnect(connection.id)}
        className="shrink-0 text-muted-foreground/50 transition-colors hover:text-destructive"
        aria-label="Disconnect account"
        loading={disconnecting}
      >
        <Trash2 size={12} />
      </CustomButton>
    </div>
  );
}
