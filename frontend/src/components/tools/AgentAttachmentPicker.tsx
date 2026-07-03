'use client';

import { Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import CheckboxField from '@/components/shared/CheckboxField';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { getAllAgents } from '@/services/agentsService';
import type { AgentDropdownItem } from '@/types/agent';
import { handleApiError } from '@/utils/helpers';

interface AgentAttachmentPickerProps {
  /** Agents currently selected (attached to their published version). */
  selectedIds: string[];
  onChange: (next: string[]) => void;
  /** True while the entity's current attachments are being fetched. */
  loading?: boolean;
  /** True when the current attachments could not be loaded — selection is
   * disabled so a blind save can't silently detach agents. */
  loadFailed?: boolean;
  /** "tool" or "MCP server" — used in the helper copy. */
  entityLabel?: string;
}

/** Checkbox list of the org's agents, shared by the tool and MCP edit forms.
 * Selections sync the entity onto each agent's PUBLISHED (live) version on
 * save — drafts and historical versions are managed from the agent editor
 * instead. Agents without a published version are skipped server-side and
 * reported back as a warning toast. */
export default function AgentAttachmentPicker({
  selectedIds,
  onChange,
  loading,
  loadFailed,
  entityLabel = 'tool',
}: AgentAttachmentPickerProps) {
  const [agents, setAgents] = useState<AgentDropdownItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    getAllAgents()
      .then((rows) => {
        if (!cancelled) setAgents(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setAgentsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return agents;
    return agents.filter((a) => a.name.toLowerCase().includes(q));
  }, [agents, search]);

  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const toggle = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(Array.from(next));
  };

  if (loading || agentsLoading) {
    return (
      <div className="flex flex-col gap-2" aria-hidden>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 animate-pulse rounded-md bg-muted/40" />
        ))}
      </div>
    );
  }

  if (loadFailed) {
    return (
      <p className="rounded-md border border-dashed border-border/70 px-3 py-4 text-[12px] text-muted-foreground">
        Couldn&apos;t load the agents currently using this {entityLabel}, so agent changes are
        disabled for this save. Reload the page to retry.
      </p>
    );
  }

  if (agents.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border/70 px-3 py-4 text-[12px] text-muted-foreground">
        No agents yet — create an agent first, then attach this {entityLabel} to it.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[11.5px] leading-relaxed text-muted-foreground">
          Applies to each agent&apos;s live (published) version. Agents without a published version
          are skipped.
        </p>
        {selectedIds.length > 0 && (
          <Badge variant="secondary" className="h-5 shrink-0 px-2 text-[11px] tabular-nums">
            {selectedIds.length} attached
          </Badge>
        )}
      </div>
      {agents.length > 6 && (
        <div className="flex items-center gap-2 rounded-md border border-border/70 bg-background px-2">
          <Search className="size-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents..."
            className="h-8 border-0 px-0 shadow-none focus-visible:ring-0"
          />
        </div>
      )}
      <div className="max-h-56 overflow-y-auto rounded-md border border-border/70 p-1.5">
        {filtered.length === 0 ? (
          <p className="px-2 py-3 text-center text-[12px] text-muted-foreground">
            Nothing matches &quot;{search}&quot;.
          </p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {filtered.map((agent) => (
              <li key={agent.id} className="rounded px-1.5 py-1 hover:bg-muted/40">
                <CheckboxField
                  id={`agent-attach-${agent.id}`}
                  label={agent.name}
                  checked={selected.has(agent.id)}
                  onCheckedChange={() => toggle(agent.id)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
