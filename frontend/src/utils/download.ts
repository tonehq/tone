/**
 * Trigger a client-side download of an in-memory CSV string as a file.
 *
 * WHAT: wraps the CSV text in a Blob, creates a temporary object URL, clicks a hidden
 * anchor, then revokes the URL. No network round-trip — the file is built in the browser.
 *
 * WHEN: reuse for every "download this as a .csv" affordance (sync sample templates, the
 * per-sync error report, etc.) instead of re-implementing the Blob/anchor dance.
 */
export function triggerCsvDownload(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
