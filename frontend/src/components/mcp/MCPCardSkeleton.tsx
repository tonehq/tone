import { Card, CardContent } from '@/components/ui/card';

const MCPCardSkeleton: React.FC = () => (
  <Card className="animate-pulse gap-0 py-0">
    <CardContent className="p-5">
      <div className="flex items-start gap-3">
        <div className="size-10 rounded-lg bg-muted" />
        <div className="flex-1 space-y-2 pt-0.5">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="h-3 w-24 rounded bg-muted" />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="h-3 w-full rounded bg-muted" />
        <div className="h-3 w-3/4 rounded bg-muted" />
      </div>
      <div className="mt-4 flex items-center justify-between pt-4">
        <div className="h-3 w-12 rounded bg-muted" />
        <div className="h-3 w-10 rounded bg-muted" />
      </div>
    </CardContent>
  </Card>
);

export default MCPCardSkeleton;
