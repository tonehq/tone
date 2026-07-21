/**
 * Trigger a client-side download of an already-built Blob (e.g. a file fetched from the
 * backend as `responseType: 'blob'`). Reuse for any binary/text file the server generates —
 * the browser never has to construct or read the file contents itself.
 */
export function triggerBlobDownload(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/**
 * Trigger a client-side download of an in-memory CSV string as a file.
 *
 * WHAT: wraps the CSV text in a Blob and downloads it via {@link triggerBlobDownload}.
 *
 * WHEN: reuse for every "download this as a .csv" affordance built from in-memory text
 * (e.g. the per-sync error report) instead of re-implementing the Blob/anchor dance.
 */
export function triggerCsvDownload(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  triggerBlobDownload(filename, blob);
}
