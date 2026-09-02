import { cn } from '@/utils/cn';

/** Nested pseudo-button inside a ``FolderCard``. Kept as ``<span role="button">``
 * because HTML doesn't allow nesting ``<button>`` inside ``<button>``, and the
 * card itself already owns the drill-in click. Handles Enter/Space, disabled
 * state, and stops propagation so the card's drill-in doesn't also fire. */
export default function FolderCardAction({
  icon,
  label,
  onActivate,
  disabled = false,
  title,
  emphasis = 'default',
  className,
}: {
  icon: React.ReactNode;
  label: string;
  onActivate: () => void;
  disabled?: boolean;
  title?: string;
  // ``danger`` matches the destructive-action visual grammar used on the
  // scenarios row (red hover) — reserved for Delete so users can't
  // mistake it for a benign action.
  emphasis?: 'default' | 'primary' | 'danger';
  className?: string;
}) {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled) onActivate();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault();
      e.stopPropagation();
      onActivate();
    }
  };

  return (
    <span
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11.5px] font-medium transition-colors',
        disabled
          ? 'cursor-not-allowed text-muted-foreground/40'
          : emphasis === 'primary'
            ? 'cursor-pointer text-foreground hover:bg-primary hover:text-primary-foreground'
            : emphasis === 'danger'
              ? 'cursor-pointer text-muted-foreground hover:bg-destructive/10 hover:text-destructive'
              : 'cursor-pointer text-muted-foreground hover:bg-muted hover:text-foreground',
        className,
      )}
      title={title}
      aria-label={label}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}
