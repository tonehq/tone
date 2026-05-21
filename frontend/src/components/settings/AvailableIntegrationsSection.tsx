'use client';

import IntegrationCard from '@/components/settings/IntegrationCard';
import SectionTitle from '@/components/settings/SectionTitle';
import type { ProviderCardConfig } from '@/constants/integrations';
import type { OAuthConnection } from '@/types/oauth';
import { ExternalLink, Key, Loader2, Plus, Zap } from 'lucide-react';

interface AvailableIntegrationsSectionProps {
  oauthProviders: ProviderCardConfig[];
  apiKeyProviders: ProviderCardConfig[];
  getConnectionsForProvider: (key: string) => OAuthConnection[];
  rowsByType: Record<string, unknown[]>;
  oauthConnecting: Record<string, boolean>;
  oauthLoading: boolean;
  onOAuthConnect: (key: string) => void;
  onAddApiKey: (providerKey: string) => void;
}

export default function AvailableIntegrationsSection({
  oauthProviders,
  apiKeyProviders,
  getConnectionsForProvider,
  rowsByType,
  oauthConnecting,
  oauthLoading,
  onOAuthConnect,
  onAddApiKey,
}: AvailableIntegrationsSectionProps) {
  const availableOAuth = oauthProviders.filter(
    (p) => getConnectionsForProvider(p.key).length === 0,
  );
  const availableApiKey = apiKeyProviders.filter((p) => (rowsByType[p.key] ?? []).length === 0);

  return (
    <>
      {availableOAuth.length > 0 && (
        <section className="mb-10">
          <SectionTitle icon={Zap} iconColor="text-muted-foreground" title="Connected Services" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {availableOAuth.map((provider) => {
              const isConnecting = oauthConnecting[provider.key] ?? false;
              return (
                <IntegrationCard
                  key={provider.key}
                  config={provider}
                  hasItems={false}
                  actionLabel="Connect"
                  actionIcon={
                    isConnecting ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <ExternalLink size={12} />
                    )
                  }
                  actionLoading={isConnecting || oauthLoading}
                  onAction={() => onOAuthConnect(provider.key)}
                />
              );
            })}
          </div>
        </section>
      )}

      {availableApiKey.length > 0 && (
        <section className="mb-10">
          <SectionTitle icon={Key} iconColor="text-muted-foreground" title="Telephony Providers" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {availableApiKey.map((provider) => (
              <IntegrationCard
                key={provider.key}
                config={provider}
                hasItems={false}
                actionLabel="Add API Key"
                actionIcon={<Plus size={12} />}
                actionLoading={false}
                onAction={() => onAddApiKey(provider.key)}
              />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
