'use client';

import { Download } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import type { ContactSyncRowError } from '@/types/contactSync';
import { triggerCsvDownload } from '@/utils/download';

/**
 * The shared "Skipped rows" error-report panel for a contact sync.
 *
 * WHAT: renders the sync's per-row errors as a scrollable ROW · CONTACT · REASON table
 * with a header count and a Download button that exports the same rows as a CSV.
 *
 * WHEN: reuse anywhere a sync's `row_errors` are shown — the live sync stepper
 * (`SyncContactsModal`) and the reopenable sync history (`SyncHistoryModal`). Renders
 * nothing when there are no row errors.
 */
export interface SyncErrorTableProps {
  rowErrors: ContactSyncRowError[];
  /** The sync id — used to name the downloaded report file. */
  syncId?: string;
  /** Panel header text; defaults to "Skipped rows (N)". */
  title?: string;
}

/** Turn the sync's per-row errors into a downloadable CSV (row is 1-based data row). */
export function buildSyncErrorReportCsv(rowErrors: ContactSyncRowError[]): string {
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const lines = rowErrors.map((e) =>
    [
      String(e.row + 1),
      esc(e.name ?? ''),
      esc(e.phone_number ?? ''),
      esc(e.field ?? ''),
      esc(e.message),
    ].join(','),
  );
  return `row,name,phone_number,field,message\n${lines.join('\n')}\n`;
}

export default function SyncErrorTable({ rowErrors, syncId, title }: SyncErrorTableProps) {
  if (rowErrors.length === 0) return null;

  const handleDownload = () => {
    triggerCsvDownload(
      `sync-errors-${syncId?.slice(0, 8) ?? 'report'}.csv`,
      buildSyncErrorReportCsv(rowErrors),
    );
  };

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="flex items-center justify-between border-b border-border bg-muted/30 px-3 py-2">
        <span className="text-sm font-medium text-foreground">
          {title ?? `Skipped rows (${rowErrors.length})`}
        </span>
        <CustomButton
          type="text"
          size="xs"
          icon={<Download className="size-3.5" />}
          onClick={handleDownload}
        >
          Download
        </CustomButton>
      </div>
      <div className="max-h-52 overflow-y-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-card text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-1.5">Row</th>
              <th className="px-3 py-1.5">Contact</th>
              <th className="px-3 py-1.5">Reason</th>
            </tr>
          </thead>
          <tbody>
            {rowErrors.map((e, i) => (
              <tr key={`${e.row}-${i}`} className="border-t border-border/60">
                <td className="whitespace-nowrap px-3 py-1.5 tabular-nums text-muted-foreground">
                  {e.row + 1}
                </td>
                <td className="px-3 py-1.5">
                  {e.name || e.phone_number || <span className="text-muted-foreground">—</span>}
                </td>
                <td className="px-3 py-1.5 text-muted-foreground">
                  {e.field ? `${e.field}: ` : ''}
                  {e.message}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
