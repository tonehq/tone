import { MASKED_API_KEY } from './constants';

interface ApiKeyMaskCellProps {
  present?: boolean;
}

const ApiKeyMaskCell = ({ present }: ApiKeyMaskCellProps) => {
  if (!present) return <span className="text-sm text-muted-foreground">-</span>;
  return (
    <span
      className="font-mono text-sm tracking-widest text-muted-foreground"
      aria-label="API key configured"
    >
      {MASKED_API_KEY}
    </span>
  );
};

export default ApiKeyMaskCell;
