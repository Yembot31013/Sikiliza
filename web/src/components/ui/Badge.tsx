import type { ReactNode } from "react";

type Tone = "neutral" | "live" | "info" | "warn" | "ok" | "pink";

type BadgeProps = {
  tone?: Tone;
  children: ReactNode;
  pulse?: boolean;
};

const tones: Record<Tone, string> = {
  neutral: "bg-white/80 text-[var(--muted)] border-[color-mix(in_srgb,var(--ink)_10%,transparent)]",
  live: "bg-[color-mix(in_srgb,var(--green)_28%,white)] text-[var(--ink)] border-[color-mix(in_srgb,var(--green)_45%,transparent)]",
  info: "bg-[color-mix(in_srgb,var(--blue)_24%,white)] text-[var(--ink)] border-[color-mix(in_srgb,var(--blue)_40%,transparent)]",
  warn: "bg-[color-mix(in_srgb,var(--orange)_26%,white)] text-[var(--ink)] border-[color-mix(in_srgb,var(--orange)_42%,transparent)]",
  ok: "bg-[color-mix(in_srgb,var(--yellow)_34%,white)] text-[var(--ink)] border-[color-mix(in_srgb,var(--yellow)_50%,transparent)]",
  pink: "bg-[color-mix(in_srgb,var(--pink)_34%,white)] text-[var(--ink)] border-[color-mix(in_srgb,var(--pink)_48%,transparent)]",
};

export function Badge({ tone = "neutral", children, pulse = false }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-[var(--font-mono)] text-[10px] font-bold uppercase tracking-[0.14em] ${tones[tone]} ${
        pulse ? "animate-[soft-pulse_1.4s_ease-in-out_infinite]" : ""
      }`}
    >
      {children}
    </span>
  );
}
