import { SAMPLE_CSV_HEADERS, SAMPLE_CSV_ROWS } from './constants';

/** Build the sample CSV text. RFC 4180 quoting: wrap any cell containing a
 * comma, quote, or newline in double quotes and double up embedded quotes. */
export function buildSampleCsv(): string {
  const escape = (v: string) => (/[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const lines = [SAMPLE_CSV_HEADERS, ...SAMPLE_CSV_ROWS].map((row) => row.map(escape).join(','));
  return `${lines.join('\n')}\n`;
}

/** Trigger a browser download for the sample CSV template. */
export function downloadSampleCsv() {
  const blob = new Blob([buildSampleCsv()], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'llm-evals-scenarios-sample.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
