import { CustomButton } from '@/components/shared';
import { Boxes, Plus } from 'lucide-react';

interface MCPEmptyStateProps {
  onCreate: () => void;
}

const MCPEmptyState: React.FC<MCPEmptyStateProps> = ({ onCreate }) => (
  <div className="flex flex-col items-center justify-center py-24">
    <span className="inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
      <Boxes className="size-5" strokeWidth={1.75} />
    </span>
    <h3 className="mt-5 font-display text-[15px] font-semibold text-foreground">
      No MCP servers yet
    </h3>
    <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-muted-foreground">
      Register a Model Context Protocol server to give your agents access to external tools, files,
      and live data.
    </p>
    <CustomButton type="primary" icon={<Plus size={15} />} onClick={onCreate} className="mt-5 h-10">
      Create MCP server
    </CustomButton>
  </div>
);

export default MCPEmptyState;
