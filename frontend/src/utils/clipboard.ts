// Write text to the clipboard, swallowing the failure clipboard access can
// throw (blocked permissions / no HTTPS in dev). Returns whether it succeeded
// so callers can decide whether to toast. The single home for the copy idiom
// that was otherwise hand-rolled per call site.
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
