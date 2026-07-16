'use client';

import { CustomModal } from '@/components/shared';
import type { ReadinessReport } from '@/types/readiness';

import ReadinessCheckList from './ReadinessCheckList';

interface ReadinessConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  /** The report that came back with warnings-only. Rendered inline so the user
   * sees what they're accepting. */
  report: ReadinessReport | null;
  /** Fires when the user chooses to publish over the warnings. */
  onConfirm: () => void | Promise<void>;
  loading?: boolean;
}

/**
 * Shown when the publish endpoint responds with `readiness_warnings`.
 * BLOCKERs are handled inline in the publish modal (button stays disabled);
 * this dialog only appears when the only obstacles are warnings and the
 * user needs to explicitly opt in.
 */
export default function ReadinessConfirmDialog({
  open,
  onClose,
  report,
  onConfirm,
  loading = false,
}: ReadinessConfirmDialogProps) {
  const warningCount = report?.summary.warnings ?? 0;
  const description =
    warningCount === 1
      ? 'Publishing this version has 1 warning. Calls will still work, but you might want to fix it first.'
      : `Publishing this version has ${warningCount} warnings. Calls will still work, but you might want to fix them first.`;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Publish anyway?"
      description={description}
      confirmText="Publish anyway"
      cancelText="Fix warnings first"
      confirmType="primary"
      confirmLoading={loading}
      onConfirm={() => void onConfirm()}
      width="sm:max-w-xl"
    >
      {report && report.checks.length > 0 && (
        <div className="max-h-72 overflow-y-auto">
          <ReadinessCheckList checks={report.checks.filter((c) => c.status === 'fail')} />
        </div>
      )}
    </CustomModal>
  );
}
