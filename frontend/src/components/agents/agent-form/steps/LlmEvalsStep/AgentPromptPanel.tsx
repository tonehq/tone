import { ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

export default function AgentPromptPanel({ prompt }: { prompt: string }) {
  // Expanded by default so users see the full prompt as they enter — it's
  // the most-referenced context in the drawer. Collapsible so long prompts
  // don't push scored scenarios off-screen.
  const [expanded, setExpanded] = useState(true);
  return (
    <section className="rounded-lg border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Agent system prompt at run time
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/70">
          {expanded ? 'Hide' : 'Show'}
        </span>
      </button>
      {expanded && (
        <div className="max-h-72 overflow-auto whitespace-pre-wrap border-t border-border/60 px-3 py-3 font-mono text-[12px] text-foreground">
          {prompt}
        </div>
      )}
    </section>
  );
}
