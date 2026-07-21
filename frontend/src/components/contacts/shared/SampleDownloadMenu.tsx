'use client';

import { Download } from 'lucide-react';
import { useState } from 'react';

import { schemasApi } from '@/lib/api/contactSchemas';
import { CustomButton } from '@/components/shared';
import { handleApiError } from '@/utils/helpers';

interface SampleDownloadMenuProps {
  /** Schema whose sample columns drive the file. */
  schemaId: string;
  /** Schema name — used to slugify the downloaded filename. */
  schemaName: string;
}

/**
 * Schema-based sample download affordance offering CSV and Excel. The file is generated
 * SERVER-SIDE (`GET /contact-schemas/{id}/sample?format=`) and streamed back — the browser
 * only triggers the download, so no example content (columns/numbers) is built in the client.
 */
export default function SampleDownloadMenu({ schemaId, schemaName }: SampleDownloadMenuProps) {
  const [downloading, setDownloading] = useState<'csv' | 'xlsx' | null>(null);

  const download = async (format: 'csv' | 'xlsx') => {
    setDownloading(format);
    try {
      await schemasApi.downloadSample(schemaId, format, schemaName);
    } catch (err) {
      handleApiError(err);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <span className="text-xs text-muted-foreground">Sample:</span>
      <CustomButton
        type="text"
        size="xs"
        icon={<Download className="size-3.5" />}
        loading={downloading === 'csv'}
        onClick={() => download('csv')}
      >
        CSV
      </CustomButton>
      <CustomButton
        type="text"
        size="xs"
        icon={<Download className="size-3.5" />}
        loading={downloading === 'xlsx'}
        onClick={() => download('xlsx')}
      >
        Excel
      </CustomButton>
    </div>
  );
}
