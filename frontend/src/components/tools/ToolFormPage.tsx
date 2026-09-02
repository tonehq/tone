'use client';

import { deleteToolAtom, fetchToolsAtom, upsertToolAtom } from '@/atoms/ToolAtom';
import { AppLoader, CustomModal } from '@/components/shared';
import AgentAttachmentPicker from '@/components/tools/AgentAttachmentPicker';
import BuiltInToolForm from '@/components/tools/BuiltInToolForm';
import CustomToolForm from '@/components/tools/CustomToolForm';
import { useGoBack } from '@/hooks/useGoBack';
import type { BuiltInToolFormData, CustomToolFormData } from '@/schemas/tool';
import { finalizeAttachmentAndRedirect } from '@/services/agentAttachmentService';
import { getAgentsByTool, getTool } from '@/services/toolService';
import type {
  Tool,
  ToolAuthType,
  ToolHttpMethod,
  ToolParametersSchema,
  ToolType,
  ToolUpsertPayload,
} from '@/types/tool';
import { readAttachContext } from '@/utils/agentAttachmentContext';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface ToolFormPageProps {
  toolId?: string;
}

export default function ToolFormPage({ toolId }: ToolFormPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isEditMode = !!toolId;

  const [, upsertToolAction] = useAtom(upsertToolAtom);
  const [, deleteToolAction] = useAtom(deleteToolAtom);
  const [, fetchTools] = useAtom(fetchToolsAtom);

  // Present only when the user reached this page via the agent config
  // "New tool" button — see ``ToolsMcpStep``.
  const attachCtx = useMemo(() => readAttachContext(searchParams), [searchParams]);
  const goBack = useGoBack('/tools');

  const templateId = searchParams.get('template_id');

  const [toolType, setToolType] = useState<ToolType>('custom');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [url, setUrl] = useState('');
  const [method, setMethod] = useState<ToolHttpMethod>('POST');
  const [parameters, setParameters] = useState<ToolParametersSchema>({});
  const [authType, setAuthType] = useState<ToolAuthType>('none');
  const [authHeaderName, setAuthHeaderName] = useState('');
  const [authApiKey, setAuthApiKey] = useState('');
  const [authBearerToken, setAuthBearerToken] = useState('');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [metaData, setMetaData] = useState<Record<string, string>>({});
  const [builtInAuthConfig, setBuiltInAuthConfig] = useState<Record<string, string>>({});
  const [oauthConnectionId, setOauthConnectionId] = useState<string | null>(null);
  const [appIntegrationId, setAppIntegrationId] = useState<string | null>(null);
  const [toolRecord, setToolRecord] = useState<Tool | null>(null);

  // Agents section — attachments sync to each agent's PUBLISHED version.
  // ``agentsTouched`` gates the payload: agent_ids is only sent when the user
  // actually changed the list, so an untouched save never rewrites attachments.
  const [attachedAgentIds, setAttachedAgentIds] = useState<string[]>([]);
  const [agentsTouched, setAgentsTouched] = useState(false);
  const [agentsLoading, setAgentsLoading] = useState(isEditMode);
  const [agentsLoadFailed, setAgentsLoadFailed] = useState(false);
  // Server-side baseline of attached agents — the detach confirmation compares
  // against this, and it's refreshed after every successful save.
  const initialAgentIdsRef = useRef<string[]>([]);
  // A save that would detach agents parks its payload here until the user
  // confirms via the modal below.
  const [pendingDetachSave, setPendingDetachSave] = useState<{
    payload: ToolUpsertPayload;
    count: number;
  } | null>(null);

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(isEditMode);

  const isBuiltIn = toolType !== 'custom';
  const markDirty = useCallback(() => setSaved(false), []);

  const loadToolData = useCallback(async () => {
    if (!toolId) return;
    setLoading(true);
    try {
      const tool: Tool = await getTool(toolId);
      setToolRecord(tool);
      setToolType(tool.tool_type ?? 'custom');
      setName(tool.name ?? '');
      setDescription(tool.description ?? '');
      setUrl(tool.url ?? '');
      setMethod(((tool.method ?? '').toUpperCase() as ToolHttpMethod) || 'POST');
      setParameters(tool.parameters ?? {});
      setAuthType((tool.auth_type as ToolAuthType) ?? 'none');
      setIsActive(tool.is_active ?? true);
      const cfg = tool.auth_config ?? {};
      setAuthHeaderName(cfg.header_name ?? '');
      setAuthApiKey(cfg.api_key ?? '');
      setAuthBearerToken(cfg.token ?? '');
      setAuthUsername(cfg.username ?? '');
      setAuthPassword(cfg.password ?? '');
      setMetaData((tool.meta_data ?? {}) as Record<string, string>);
      setBuiltInAuthConfig((tool.auth_config ?? {}) as Record<string, string>);
      setOauthConnectionId(tool.oauth_connection_id ?? null);
      setAppIntegrationId(tool.app_integration_id ?? null);
      setSaved(true);
      // Attachments load separately: a failure here disables the Agents
      // section (so a save can't blindly detach) without killing the form.
      try {
        const refs = await getAgentsByTool(toolId);
        const ids = refs.map((r) => r.id);
        setAttachedAgentIds(ids);
        initialAgentIdsRef.current = ids;
        setAgentsLoadFailed(false);
      } catch {
        setAgentsLoadFailed(true);
      } finally {
        setAgentsLoading(false);
      }
    } catch (error) {
      handleApiError(error);
      router.push('/tools');
    } finally {
      setLoading(false);
    }
  }, [toolId, router]);

  useEffect(() => {
    if (isEditMode) loadToolData();
  }, [isEditMode, loadToolData]);

  useEffect(() => {
    if (!templateId || isEditMode) return;
    setLoading(true);
    getTool(templateId)
      .then((template) => {
        setToolType(template.tool_type ?? 'custom');
        setParameters(template.parameters ?? {});
      })
      .catch((err) => handleApiError(err))
      .finally(() => setLoading(false));
  }, [templateId, isEditMode]);

  // OAuth-backed custom tools resolve credentials from the linked connection
  // at call time, so they never carry inline ``auth_config`` — return ``null``
  // for both ``oauth`` and ``none`` to keep stale fields from leaking into
  // the payload when the user switches auth types.
  const buildAuthConfig = useCallback((): Record<string, string> | null => {
    switch (authType) {
      case 'api_key':
        return { header_name: authHeaderName || 'X-API-Key', api_key: authApiKey };
      case 'bearer':
        return { token: authBearerToken };
      case 'basic':
        return { username: authUsername, password: authPassword };
      default:
        return null;
    }
  }, [authType, authHeaderName, authApiKey, authBearerToken, authUsername, authPassword]);

  const executeSave = async (payload: ToolUpsertPayload, skipDetachConfirm = false) => {
    // Detaching is destructive for live agents — a save that would remove the
    // tool from previously-attached agents must be confirmed first. The
    // payload is parked and re-submitted from the modal's confirm button.
    if (payload.agent_ids && !skipDetachConfirm) {
      const selected = new Set(payload.agent_ids);
      const removedCount = initialAgentIdsRef.current.filter((id) => !selected.has(id)).length;
      if (removedCount > 0) {
        setPendingDetachSave({ payload, count: removedCount });
        return;
      }
    }
    setSaving(true);
    try {
      const savedTool = await upsertToolAction(payload);
      const summary = savedTool?.attachment_summary;
      showToast.success(
        isEditMode ? 'Tool updated successfully' : 'Tool created successfully',
        summary && (summary.attached > 0 || summary.detached > 0)
          ? `Attached to ${summary.attached} agent(s), detached from ${summary.detached}.`
          : undefined,
      );
      if (savedTool?.attachment_warnings?.length) {
        showToast.warning(
          'Some agent attachments were skipped',
          savedTool.attachment_warnings.join(' • '),
          8,
        );
      }
      if (payload.agent_ids) initialAgentIdsRef.current = payload.agent_ids;
      setAgentsTouched(false);
      setSaved(true);
      await fetchTools();
      if (isEditMode) return;
      // When launched from the agent config page, attach the created tool to
      // that agent's viewing version and bounce back; otherwise land on the
      // tools list. See ``finalizeAttachmentAndRedirect`` for the shared flow.
      await finalizeAttachmentAndRedirect({
        router,
        attachCtx,
        kind: 'tool',
        itemId: savedTool?.id,
        attachedMessage: 'Tool attached to the agent version',
        fallbackRedirect: '/tools',
      });
    } catch (error) {
      handleApiError(error);
    } finally {
      setSaving(false);
    }
  };

  const handleBuiltInSave = async (data: BuiltInToolFormData) => {
    const hasAuthConfig = Object.values(builtInAuthConfig).some((v) => v);
    const payload: ToolUpsertPayload = {
      ...(isEditMode && toolId ? { id: toolId } : {}),
      name: data.name.trim(),
      description: data.description.trim(),
      tool_type: toolType,
      parameters,
      meta_data: metaData,
      ...(hasAuthConfig ? { auth_config: builtInAuthConfig } : {}),
      oauth_connection_id: oauthConnectionId,
      app_integration_id: appIntegrationId,
      is_active: true,
      ...(agentsTouched && !agentsLoadFailed ? { agent_ids: attachedAgentIds } : {}),
    };
    await executeSave(payload);
  };

  const handleCustomSave = async (data: CustomToolFormData) => {
    // Connection-capable auth types (oauth / bearer / api_key) can carry a
    // credential link via ``oauth_connection_id`` (resolved fresh at call
    // time; wins over inline ``auth_config``). Send the picker fields only on
    // those branches so switching to none/basic correctly drops the binding.
    const usesConnection = authType === 'oauth' || authType === 'bearer' || authType === 'api_key';
    const payload: ToolUpsertPayload = {
      ...(isEditMode && toolId ? { id: toolId } : {}),
      name: data.name.trim(),
      description: data.description.trim(),
      url: data.url.trim(),
      method,
      parameters,
      auth_type: authType,
      auth_config: buildAuthConfig(),
      oauth_connection_id: usesConnection ? oauthConnectionId : null,
      app_integration_id: usesConnection ? appIntegrationId : null,
      is_active: isActive,
      ...(agentsTouched && !agentsLoadFailed ? { agent_ids: attachedAgentIds } : {}),
    };
    await executeSave(payload);
  };

  const handleAttachedAgentsChange = useCallback((ids: string[]) => {
    setAttachedAgentIds(ids);
    setAgentsTouched(true);
    setSaved(false);
  }, []);

  const handleParametersChange = useCallback((schema: ToolParametersSchema) => {
    setParameters(schema);
  }, []);

  const handleBack = goBack;

  const handleDelete = useCallback(async () => {
    if (!toolId) return;
    try {
      await deleteToolAction(toolId);
      showToast.success('Tool deleted successfully');
      await fetchTools();
      router.push('/tools');
    } catch (error) {
      handleApiError(error);
    }
  }, [toolId, deleteToolAction, fetchTools, router]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <AppLoader label={isEditMode ? 'Loading tool...' : 'Loading...'} className="min-h-0" />
      </div>
    );
  }

  const agentsSection = (
    <AgentAttachmentPicker
      selectedIds={attachedAgentIds}
      onChange={handleAttachedAgentsChange}
      loading={agentsLoading}
      loadFailed={agentsLoadFailed}
      entityLabel="tool"
    />
  );

  const detachConfirmModal = (
    <CustomModal
      open={!!pendingDetachSave}
      onClose={() => setPendingDetachSave(null)}
      title="Detach from agents?"
      description={
        pendingDetachSave
          ? `Saving will detach this tool from ${pendingDetachSave.count} agent${
              pendingDetachSave.count === 1 ? '' : 's'
            } currently using it on their live version. Calls on ${
              pendingDetachSave.count === 1 ? 'that agent' : 'those agents'
            } will no longer see this tool.`
          : undefined
      }
      confirmText="Detach and save"
      confirmType="danger"
      confirmLoading={saving}
      onConfirm={() => {
        if (!pendingDetachSave) return;
        const { payload } = pendingDetachSave;
        setPendingDetachSave(null);
        executeSave(payload, true);
      }}
    />
  );

  if (isBuiltIn) {
    return (
      <>
        {detachConfirmModal}
        <BuiltInToolForm
          toolType={toolType}
          name={name}
          description={description}
          metaData={metaData}
          parameters={parameters}
          toolRecord={toolRecord}
          isEditMode={isEditMode}
          saving={saving}
          saved={saved}
          oauthConnectionId={oauthConnectionId}
          appIntegrationId={appIntegrationId}
          onMetaDataChange={setMetaData}
          authConfig={builtInAuthConfig}
          onAuthConfigChange={setBuiltInAuthConfig}
          onOAuthConnectionIdChange={setOauthConnectionId}
          onAppIntegrationIdChange={setAppIntegrationId}
          onSave={handleBuiltInSave}
          onDelete={isEditMode ? handleDelete : undefined}
          onBack={handleBack}
          onDirty={markDirty}
          agentsSection={agentsSection}
        />
      </>
    );
  }

  return (
    <>
      {detachConfirmModal}
      <CustomToolForm
        name={name}
        description={description}
        url={url}
        method={method}
        parameters={parameters}
        authType={authType}
        authHeaderName={authHeaderName}
        authApiKey={authApiKey}
        authBearerToken={authBearerToken}
        authUsername={authUsername}
        authPassword={authPassword}
        appIntegrationId={appIntegrationId}
        oauthConnectionId={oauthConnectionId}
        isActive={isActive}
        isEditMode={isEditMode}
        saving={saving}
        onMethodChange={setMethod}
        onParametersChange={handleParametersChange}
        onAuthTypeChange={setAuthType}
        onAuthHeaderNameChange={setAuthHeaderName}
        onAuthApiKeyChange={setAuthApiKey}
        onAuthBearerTokenChange={setAuthBearerToken}
        onAuthUsernameChange={setAuthUsername}
        onAuthPasswordChange={setAuthPassword}
        onAppIntegrationIdChange={setAppIntegrationId}
        onOAuthConnectionIdChange={setOauthConnectionId}
        onIsActiveChange={setIsActive}
        onSave={handleCustomSave}
        onBack={handleBack}
        agentsSection={agentsSection}
      />
    </>
  );
}
