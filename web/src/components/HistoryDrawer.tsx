import type { Caption } from "../types";
import { languageBadge } from "../lib/labels";
import { Button } from "./ui/Button";

type HistoryDrawerProps = {
  open: boolean;
  captions: Caption[];
  onClose: () => void;
  onClear: () => void;
};

export function HistoryDrawer({ open, captions, onClose, onClear }: HistoryDrawerProps) {
  if (!open) return null;

  return (
    <aside
      className="fade-in flex min-h-0 w-full shrink-0 flex-col overflow-hidden rounded-[var(--radius-32)] border border-white/70 bg-[color-mix(in_srgb,var(--white)_88%,var(--cream))] shadow-[var(--shadow-soft)] max-lg:max-h-[38vh] lg:h-full lg:w-[min(340px,34vw)]"
      aria-label="Caption history"
    >
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[color-mix(in_srgb,var(--ink)_8%,transparent)] px-4 py-4">
        <div className="min-w-0">
          <p className="label-mono">History</p>
          <p className="mt-1 truncate text-sm text-[var(--muted)]">
            {captions.length} line{captions.length === 1 ? "" : "s"} · scroll inside
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" className="min-h-9 px-3 text-xs" onClick={onClear}>
            Clear
          </Button>
          <Button variant="ghost" className="min-h-9 px-3 text-xs" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4">
        {captions.length === 0 ? (
          <p className="text-sm leading-6 text-[var(--muted)]">
            Finalized lines collect here while you keep watching the shared tab.
          </p>
        ) : (
          <ol className="space-y-4">
            {captions
              .slice()
              .reverse()
              .map((caption) => {
                const lang = languageBadge(caption.language);
                return (
                  <li
                    key={`${caption.id}-${caption.endMs}`}
                    className="border-b border-[color-mix(in_srgb,var(--ink)_8%,transparent)] pb-4 last:border-b-0"
                  >
                    {lang ? (
                      <p className="label-mono mb-1.5 text-[9px] text-[var(--muted)]">{lang}</p>
                    ) : null}
                    {caption.source ? (
                      <p className="mb-1 text-xs leading-5 text-[var(--muted)] text-pretty">
                        {caption.source}
                      </p>
                    ) : null}
                    <p className="text-sm leading-6 text-[var(--ink)] text-pretty">
                      {caption.translation}
                    </p>
                  </li>
                );
              })}
          </ol>
        )}
      </div>
    </aside>
  );
}
