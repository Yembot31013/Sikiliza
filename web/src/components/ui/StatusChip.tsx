import type { ReactNode } from "react";

type StatusChipProps = {
  active?: boolean;
  done?: boolean;
  children: ReactNode;
};

export function StatusChip({ active = false, done = false, children }: StatusChipProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1.5 font-[var(--font-mono)] text-[10px] font-bold uppercase tracking-[0.12em] transition-colors duration-150 ${
        active
          ? "border-[color-mix(in_srgb,var(--blue)_50%,transparent)] bg-[color-mix(in_srgb,var(--blue)_18%,white)] text-[var(--ink)]"
          : done
            ? "border-[color-mix(in_srgb,var(--green)_40%,transparent)] bg-[color-mix(in_srgb,var(--green)_14%,white)] text-[var(--ink)]"
            : "border-[color-mix(in_srgb,var(--ink)_10%,transparent)] bg-white/70 text-[var(--muted)]"
      }`}
    >
      {children}
    </span>
  );
}
