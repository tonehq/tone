'use client';

import { getProviderLogoUrl } from '@/components/service-providers/constants';
import { cn } from '@/utils/cn';
import { Plug } from 'lucide-react';
import { useEffect, useState } from 'react';

interface IntegrationLogoProps {
  /** Catalog slug — used to resolve a logo from the static registry when no
   *  ``iconUrl`` is provided by the backend. */
  slug: string;
  /** Admin-supplied logo URL from ``app_integrations.icon_url``. Takes
   *  precedence over the registry. */
  iconUrl?: string | null;
  /** Provider display name, used for the ``<img>`` alt text. */
  name?: string;
  /** Rendered image pixel size (the outer plate sizing is controlled by the
   *  consumer — this component only renders the inner mark). */
  imgSize?: number;
  className?: string;
}

/**
 * Renders a single integration provider's brand mark for the integrations
 * page. Resolution order:
 *   1. ``iconUrl`` (admin-configured on ``app_integrations.icon_url``)
 *   2. Static ``PROVIDER_LOGOS`` lookup by slug
 *   3. Neutral plug icon fallback
 *
 * The component owns its own ``onError`` failure state so a broken remote
 * favicon transparently falls through to the plug icon without leaving a
 * broken-image placeholder in the tile.
 */
export default function IntegrationLogo({
  slug,
  iconUrl,
  name,
  imgSize = 22,
  className,
}: IntegrationLogoProps) {
  const resolvedUrl = iconUrl || getProviderLogoUrl(slug);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [resolvedUrl]);

  if (!resolvedUrl || failed) {
    return <Plug className={cn('size-4 text-muted-foreground', className)} aria-hidden />;
  }

  return (
    <img
      src={resolvedUrl}
      alt={name ?? slug}
      width={imgSize}
      height={imgSize}
      className={cn('object-contain', className)}
      style={{ width: imgSize, height: imgSize }}
      onError={() => setFailed(true)}
    />
  );
}
