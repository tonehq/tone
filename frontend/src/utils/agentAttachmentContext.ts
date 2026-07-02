/** URL-parameter contract used to plumb an "attach to this agent version"
 * intent through the Tool / MCP create pages.
 *
 * When the user clicks "New tool" / "New MCP server" from the agent config
 * page, the current agent id + agent config (version) id are appended to the
 * destination URL. After the create succeeds, the form page reads them back
 * and attaches the newly-created row to that specific version — landing the
 * user back on the same editor version with the new attachment already wired.
 *
 * Kept in one file so query-param key names, encoding, and redirect-back
 * URL construction never drift between call sites.
 */

export interface AgentAttachmentContext {
  agentId: string;
  configId: string;
}

export const ATTACH_PARAM_AGENT_ID = 'attach_agent_id';
export const ATTACH_PARAM_CONFIG_ID = 'attach_config_id';

/** Read the two params off any ``URLSearchParams``-like source. Returns
 * ``null`` unless BOTH are present — a half-set context isn't actionable. */
export function readAttachContext(
  search: URLSearchParams | Readonly<URLSearchParams> | null | undefined,
): AgentAttachmentContext | null {
  if (!search) return null;
  const agentId = search.get(ATTACH_PARAM_AGENT_ID);
  const configId = search.get(ATTACH_PARAM_CONFIG_ID);
  return agentId && configId ? { agentId, configId } : null;
}

/** Merge the attach params onto an existing pathname, preserving any query
 * string already on it. Callers pass the base path (``/tools/create`` etc.)
 * and this returns a fully-formed URL for ``router.push``. */
export function withAttachContext(basePath: string, ctx: AgentAttachmentContext): string {
  const [path, existingQuery = ''] = basePath.split('?');
  const params = new URLSearchParams(existingQuery);
  params.set(ATTACH_PARAM_AGENT_ID, ctx.agentId);
  params.set(ATTACH_PARAM_CONFIG_ID, ctx.configId);
  return `${path}?${params.toString()}`;
}

/** The editor URL to redirect back to after the attach succeeds. ``agentType``
 * comes from the ``AgentDetail`` returned by the update call, so callers don't
 * hard-code inbound / outbound. */
export function editorReturnUrl(agentType: string, agentId: string): string {
  return `/agents/edit/${agentType}/${agentId}/tools`;
}
