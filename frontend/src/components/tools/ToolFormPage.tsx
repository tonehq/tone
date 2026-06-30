'use client';

import { deleteToolAtom, fetchToolsAtom, upsertToolAtom } from '@/atoms/ToolAtom';
import { AppLoader } from '@/components/shared';
import BuiltInToolForm from '@/components/tools/BuiltInToolForm';
import CustomToolForm from '@/components/tools/CustomToolForm';
import { useGoBack } from '@/hooks/useGoBack';
import type { BuiltInToolFormData, CustomToolFormData } from '@/schemas/tool';
import { getTool } from '@/services/toolService';
import type {
  Tool,
  ToolAuthType,
  ToolHttpMethod,
  ToolParametersSchema,
  ToolType,
  ToolUpsertPayload,
} from '@/types/tool';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

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
      .catch(() => {})
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

  const executeSave = async (payload: ToolUpsertPayload) => {
    setSaving(true);
    try {
      await upsertToolAction(payload);
      showToast.success(isEditMode ? 'Tool updated successfully' : 'Tool created successfully');
      setSaved(true);
      await fetchTools();
      if (!isEditMode) router.push('/tools');
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
    };
    await executeSave(payload);
  };

  const handleCustomSave = async (data: CustomToolFormData) => {
    // OAuth-backed custom tools carry their credential link via
    // ``oauth_connection_id`` (resolved fresh at call time) instead of
    // ``auth_config``. Send the picker fields only on the OAuth branch so
    // switching auth types away from OAuth correctly drops the binding.
    const isOAuth = authType === 'oauth';
    const payload: ToolUpsertPayload = {
      ...(isEditMode && toolId ? { id: toolId } : {}),
      name: data.name.trim(),
      description: data.description.trim(),
      url: data.url.trim(),
      method,
      parameters,
      auth_type: authType,
      auth_config: buildAuthConfig(),
      oauth_connection_id: isOAuth ? oauthConnectionId : null,
      app_integration_id: isOAuth ? appIntegrationId : null,
      is_active: isActive,
    };
    await executeSave(payload);
  };

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

  if (isBuiltIn) {
    return (
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
      />
    );
  }

  return (
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
    />
  );
}
