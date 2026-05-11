'use client';

import {
  deleteChannelAtom,
  loadableChannelsAtom,
  upsertChannelAtom,
} from '@/atoms/IntegrationAtom';
import ActiveConnectionsSection from '@/components/settings/ActiveConnectionsSection';
import AvailableIntegrationsSection from '@/components/settings/AvailableIntegrationsSection';
import { API_KEY_PROVIDERS, OAUTH_PROVIDERS } from '@/constants/integrations';
import {
  disconnectOAuth,
  getOAuthAuthorizeUrl,
  getOAuthConnections,
} from '@/services/oauthService';
import type { IntegrationRow } from '@/types/integration';
import type { OAuthConnection } from '@/types/oauth';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import AddChannelModal from './AddChannelModal';

interface IntegrationsProps {
  refreshKey?: string | null;
}

export default function Integrations({ refreshKey }: IntegrationsProps) {
  const [mounted, setMounted] = useState(false);
  const [channelsLoadable] = useAtom(loadableChannelsAtom);
  const [, upsertChannel] = useAtom(upsertChannelAtom);
  const [, removeChannel] = useAtom(deleteChannelAtom);
  const [modalOpen, setModalOpen] = useState(false);
  const [editRow, setEditRow] = useState<IntegrationRow | null>(null);

  const [allConnections, setAllConnections] = useState<OAuthConnection[]>([]);
  const [oauthLoading, setOauthLoading] = useState(true);
  const [oauthConnecting, setOauthConnecting] = useState<Record<string, boolean>>({});
  const [disconnectingId, setDisconnectingId] = useState<number | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchConnections = useCallback(async () => {
    setOauthLoading(true);
    try {
      const connections = await getOAuthConnections();
      setAllConnections(connections);
    } catch {
      setAllConnections([]);
    } finally {
      setOauthLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mounted) fetchConnections();
  }, [mounted, fetchConnections]);

  useEffect(() => {
    if (refreshKey) fetchConnections();
  }, [refreshKey, fetchConnections]);

  const getConnectionsForProvider = useCallback(
    (providerKey: string) =>
      allConnections.filter((c) => c.provider === providerKey && c.is_active),
    [allConnections],
  );

  const handleOAuthConnect = useCallback(async (providerKey: string) => {
    setOauthConnecting((prev) => ({ ...prev, [providerKey]: true }));
    try {
      const authUrl = await getOAuthAuthorizeUrl(providerKey);
      window.location.href = authUrl;
    } catch (error) {
      handleApiError(error);
      setOauthConnecting((prev) => ({ ...prev, [providerKey]: false }));
    }
  }, []);

  const handleOAuthDisconnect = useCallback(async (connectionId: number) => {
    setDisconnectingId(connectionId);
    try {
      await disconnectOAuth(connectionId);
      setAllConnections((prev) => prev.filter((c) => c.id !== connectionId));
      showToast.success('Account disconnected');
    } catch (error) {
      handleApiError(error);
    } finally {
      setDisconnectingId(null);
    }
  }, []);

  const rows: IntegrationRow[] = channelsLoadable.state === 'hasData' ? channelsLoadable.data : [];

  const rowsByType = useMemo(() => {
    const map: Record<string, IntegrationRow[]> = {};
    for (const row of rows) {
      const type = (row.type ?? 'twilio').toLowerCase();
      if (!map[type]) map[type] = [];
      map[type].push(row);
    }
    return map;
  }, [rows]);

  const handleAddApiKey = useCallback(() => {
    setEditRow(null);
    setModalOpen(true);
  }, []);

  const handleEdit = useCallback((row: IntegrationRow) => {
    setEditRow(row);
    setModalOpen(true);
  }, []);

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditRow(null);
  };

  const handleSubmit = async (data: {
    id?: number;
    name: string;
    type: string;
    auth_token: string;
    account_sid: string;
  }) => {
    const payload = {
      ...(data.id ? { id: data.id } : {}),
      name: data.name,
      type: data.type,
      meta_data: {
        account_sid: data.account_sid,
        auth_token: data.auth_token,
      },
    };

    try {
      await upsertChannel(payload as any);
      showToast.success(
        data.id ? 'Integration updated successfully' : 'Integration created successfully',
      );
    } catch (err) {
      handleApiError(err);
      throw new Error('API call failed');
    }
  };

  const handleDelete = useCallback(
    async (id: number) => {
      try {
        await removeChannel(id);
        showToast.success('Integration deleted successfully');
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeChannel],
  );

  if (!mounted) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4">
        <Loader2 className="size-10 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="mb-10">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Integrations</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Connect services and manage credentials to power your voice agents.
        </p>
      </div>

      <ActiveConnectionsSection
        oauthProviders={OAUTH_PROVIDERS}
        apiKeyProviders={API_KEY_PROVIDERS}
        getConnectionsForProvider={getConnectionsForProvider}
        rowsByType={rowsByType}
        oauthConnecting={oauthConnecting}
        disconnectingId={disconnectingId}
        onOAuthConnect={handleOAuthConnect}
        onOAuthDisconnect={handleOAuthDisconnect}
        onAddApiKey={handleAddApiKey}
        onEditRow={handleEdit}
        onDeleteRow={handleDelete}
      />

      <AvailableIntegrationsSection
        oauthProviders={OAUTH_PROVIDERS}
        apiKeyProviders={API_KEY_PROVIDERS}
        getConnectionsForProvider={getConnectionsForProvider}
        rowsByType={rowsByType}
        oauthConnecting={oauthConnecting}
        oauthLoading={oauthLoading}
        onOAuthConnect={handleOAuthConnect}
        onAddApiKey={handleAddApiKey}
      />

      <AddChannelModal
        open={modalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmit}
        editData={editRow}
      />
    </div>
  );
}
