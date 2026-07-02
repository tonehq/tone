import { getAgent, updateAgentVersion } from '@/services/agentsService';
import type { AgentDetail } from '@/types/agent';
import { editorReturnUrl, type AgentAttachmentContext } from '@/utils/agentAttachmentContext';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/** Which attachment surface the caller is appending to. */
export type AttachmentKind = 'tool' | 'mcp_server';

interface AppendAttachmentArgs {
  agentId: string;
  /** The specific agent-config (version) row to attach to. Non-optional — we
   * never want to silently attach to whatever the "current" version happens
   * to be at request time. */
  configId: string;
  kind: AttachmentKind;
  itemId: string;
}

/** Append a freshly-created tool or MCP server to a specific agent version.
 *
 * Uses the existing ``get_agent`` + ``update_version`` endpoints so no new
 * backend surface is needed. Fetching the current attachment set (one call)
 * and re-sending the deduped list (one call) is two total requests — O(1),
 * not N+1 — and reuses the same version-scoped path Save already exercises.
 *
 * Never sends ``config`` in the update payload, so the pre-existing
 * ``AgentConfigRequest`` validator can't reject the request when the target
 * agent is in a workflow-mode-with-null-workflow-id state.
 */
export async function appendAttachmentToAgentVersion(
  args: AppendAttachmentArgs,
): Promise<AgentDetail> {
  const { agentId, configId, kind, itemId } = args;
  const detail = await getAgent(agentId, configId);

  const currentIds =
    kind === 'tool' ? detail.tools.map((t) => t.id) : detail.mcp_servers.map((m) => m.id);
  // ``Set`` dedup — the newly-created row is normally new to this version,
  // but re-navigation could resend the same id; keep the sync idempotent.
  const nextIds = Array.from(new Set([...currentIds, itemId]));

  const payload = kind === 'tool' ? { tool_ids: nextIds } : { mcp_server_ids: nextIds };

  return updateAgentVersion(agentId, {
    ...payload,
    source_config_id: configId,
  });
}

/** Minimal router shape used by {@link finalizeAttachmentAndRedirect}. Kept
 * as a structural type so callers can pass Next's ``AppRouterInstance`` or
 * any test double with a compatible ``push``. */
interface Redirector {
  push: (url: string) => void;
}

interface FinalizeAttachmentArgs {
  router: Redirector;
  /** When ``null`` the caller wasn't opened from an agent editor — skip the
   * attach step and just go to ``fallbackRedirect``. */
  attachCtx: AgentAttachmentContext | null;
  kind: AttachmentKind;
  itemId: string | undefined;
  /** Toast text shown on a successful attach. */
  attachedMessage: string;
  /** Where to land the user when there is no attach context OR the attach
   * step failed (the newly-created row still exists in either case). */
  fallbackRedirect: string;
}

/** Shared "attach the freshly-created row to the source agent version, then
 * redirect" step used by both {@link ToolFormPage} and {@link MCPFormPage}.
 *
 * Behaviour:
 *  - No attach context or missing ``itemId``: bounce to ``fallbackRedirect``.
 *  - Attach succeeds: toast + redirect to the agent's Tools & MCP editor tab
 *    for the returned agent type.
 *  - Attach fails: surface the error via ``handleApiError`` but still bounce
 *    to ``fallbackRedirect`` so the user doesn't get stuck (their new row
 *    exists — they can wire it up manually).
 */
export async function finalizeAttachmentAndRedirect(args: FinalizeAttachmentArgs): Promise<void> {
  const { router, attachCtx, kind, itemId, attachedMessage, fallbackRedirect } = args;
  if (attachCtx && itemId) {
    try {
      const updated = await appendAttachmentToAgentVersion({
        agentId: attachCtx.agentId,
        configId: attachCtx.configId,
        kind,
        itemId,
      });
      showToast.success(attachedMessage);
      router.push(editorReturnUrl(updated.agent_type, updated.id));
      return;
    } catch (err) {
      handleApiError(err);
    }
  }
  router.push(fallbackRedirect);
}
