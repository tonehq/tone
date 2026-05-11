'use client';

import ApiKeyCredentialRow from '@/components/settings/ApiKeyCredentialRow';
import ConnectedAccountRow from '@/components/settings/ConnectedAccountRow';
import IntegrationCard from '@/components/settings/IntegrationCard';
import SectionTitle from '@/components/settings/SectionTitle';
import type { ProviderCardConfig } from '@/constants/integrations';
import type { IntegrationRow } from '@/types/integration';
import type { OAuthConnection } from '@/types/oauth';
import { Loader2, Plus, Zap } from 'lucide-react';

interface ActiveConnectionsSectionProps {
  oauthProviders: ProviderCardConfig[];
  apiKeyProviders: ProviderCardConfig[];
  getConnectionsForProvider: (key: string) => OAuthConnection[];
  rowsByType: Record<string, IntegrationRow[]>;
  oauthConnecting: Record<string, boolean>;
  disconnectingId: number | null;
  onOAuthConnect: (key: string) => void;
  onOAuthDisconnect: (id: number) => void;
  onAddApiKey: () => void;
  onEditRow: (row: IntegrationRow) => void;
  onDeleteRow: (id: number) => void;
}

export default function ActiveConnectionsSection({
  oauthProviders,
  apiKeyProviders,
  getConnectionsForProvider,
  rowsByType,
  oauthConnecting,
  disconnectingId,
  onOAuthConnect,
  onOAuthDisconnect,
  onAddApiKey,
  onEditRow,
  onDeleteRow,
}: ActiveConnectionsSectionProps) {
  const activeOAuth = oauthProviders.filter((p) => getConnectionsForProvider(p.key).length > 0);
  const activeApiKey = apiKeyProviders.filter((p) => (rowsByType[p.key] ?? []).length > 0);

  if (activeOAuth.length === 0 && activeApiKey.length === 0) return null;

  return (
    <section className="mb-10">
      <SectionTitle icon={Zap} iconColor="text-primary" title="Active Connections" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {activeOAuth.map((provider) => {
          const connections = getConnectionsForProvider(provider.key);
          const isConnecting = oauthConnecting[provider.key] ?? false;
          return (
            <IntegrationCard
              key={provider.key}
              config={provider}
              hasItems
              actionLabel="Add Account"
              actionIcon={
                isConnecting ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />
              }
              actionLoading={isConnecting}
              onAction={() => onOAuthConnect(provider.key)}
            >
              {connections.map((conn) => (
                <ConnectedAccountRow
                  key={conn.id}
                  connection={conn}
                  onDisconnect={onOAuthDisconnect}
                  disconnecting={disconnectingId === conn.id}
                />
              ))}
            </IntegrationCard>
          );
        })}
        {activeApiKey.map((provider) => {
          const providerRows = rowsByType[provider.key] ?? [];
          return (
            <IntegrationCard
              key={provider.key}
              config={provider}
              hasItems
              actionLabel="Add Key"
              actionIcon={<Plus size={12} />}
              actionLoading={false}
              onAction={onAddApiKey}
            >
              {providerRows.map((row) => (
                <ApiKeyCredentialRow
                  key={row.id}
                  row={row}
                  onEdit={onEditRow}
                  onDelete={onDeleteRow}
                />
              ))}
            </IntegrationCard>
          );
        })}
      </div>
    </section>
  );
}
