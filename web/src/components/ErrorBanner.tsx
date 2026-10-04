import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";

type ErrorBannerProps = {
  message: string;
  onRetry: () => void;
  onDismiss?: () => void;
};

export function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div
      className="fade-in mx-auto flex w-full max-w-3xl flex-wrap items-center gap-3 rounded-[var(--radius-22)] border border-[color-mix(in_srgb,var(--orange)_35%,transparent)] bg-[color-mix(in_srgb,var(--pink)_18%,white)] px-4 py-3 shadow-[var(--shadow-soft)]"
      role="alert"
    >
      <Badge tone="warn">Recoverable</Badge>
      <p className="min-w-0 flex-1 text-sm leading-6 text-[var(--ink)]">{message}</p>
      <Button className="min-h-10" onClick={onRetry}>
        Retry
      </Button>
      {onDismiss ? (
        <Button variant="ghost" className="min-h-10" onClick={onDismiss}>
          Dismiss
        </Button>
      ) : null}
    </div>
  );
}
