'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import type { ReadinessReport } from '@/types/readiness';

import ReadinessCheckList from './ReadinessCheckList';

interface ReadinessBlockedDialogProps {
  open: boolean;
  onClose: () => void;
  /** The deep report the publish gate returned with BLOCKER-level failures.
   * Rendered inline so the user sees exactly what to fix. */
  report: ReadinessReport | null;
}

/**
 * Shown when the publish endpoint responds with `readiness_blocked`.
 *
 * Blockers can never be forced (unlike warnings — see {@link
 * ReadinessConfirmDialog}), so this dialog is informational: it surfaces the
 * exact failing checks (message + how to fix) from the gate's deep report
 * instead of a bare "N blocker(s)" toast. Rendering reuses the shared
 * {@link ReadinessCheckList}, so it stays consistent with the readiness drawer
 * and the warnings dialog.
 */
export default function ReadinessBlockedDialog({
  open,
  onClose,
  report,
}: ReadinessBlockedDialogProps) {
  const blockerCount = report?.summary.blockers ?? 0;
  const description =
    blockerCount === 1
      ? 'This version has 1 blocker that would make calls fail. Fix it, then publish again.'
      : `This version has ${blockerCount} blockers that would make calls fail. Fix them, then publish again.`;

  const footer = (
    <CustomButton type="primary" onClick={onClose}>
      Got it
    </CustomButton>
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Cannot publish this version"
      description={description}
      footer={footer}
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
