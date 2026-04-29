import { Card, CardContent } from '@/components/ui/card';

const OrganizationCardSkeleton: React.FC = () => (
  <Card className="animate-pulse gap-0 py-0">
    <CardContent className="p-5">
      <div className="flex items-start gap-4">
        <div className="size-12 rounded-xl bg-muted" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 rounded bg-muted" />
          <div className="h-3 w-20 rounded bg-muted" />
        </div>
      </div>
      <div className="mt-4 flex gap-3">
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-3 w-24 rounded bg-muted" />
      </div>
    </CardContent>
  </Card>
);

export default OrganizationCardSkeleton;
