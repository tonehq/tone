import { CustomButton, IconChip } from '@/components/shared';
import { Boxes, Plus } from 'lucide-react';

interface MCPEmptyStateProps {
  onCreate: () => void;
}

const MCPEmptyState: React.FC<MCPEmptyStateProps> = ({ onCreate }) => (
  <div className="flex flex-col items-center justify-center py-24">
    <IconChip icon={<Boxes strokeWidth={1.75} />} tone="primary" size="2xl" />
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
