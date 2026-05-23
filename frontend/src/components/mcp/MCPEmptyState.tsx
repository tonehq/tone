import { CustomButton } from '@/components/shared';
import { Boxes, Plus } from 'lucide-react';

interface MCPEmptyStateProps {
  onCreate: () => void;
}

const MCPEmptyState: React.FC<MCPEmptyStateProps> = ({ onCreate }) => (
  <div className="flex flex-col items-center justify-center py-24">
    <div className="flex size-16 items-center justify-center rounded-2xl bg-primary/10">
      <Boxes className="size-8 text-primary" />
    </div>
    <h3 className="mt-5 text-[15px] font-semibold text-foreground">No MCP servers yet</h3>
    <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-muted-foreground">
      Register a Model Context Protocol server to give your agents access to external tools, files,
      and live data.
    </p>
    <CustomButton type="primary" icon={<Plus size={14} />} onClick={onCreate} className="mt-5">
      Create MCP Server
    </CustomButton>
  </div>
);

export default MCPEmptyState;
