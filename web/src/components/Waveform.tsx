import type { ReactNode } from "react";

type WaveformProps = {
  level: number;
  active?: boolean;
  tone?: "blue" | "green" | "orange";
};

const BARS = [0.35, 0.62, 0.95, 0.48, 0.78, 0.4, 0.88, 0.55, 0.7, 0.42, 0.92, 0.5];

const toneColor = {
  blue: "bg-[var(--blue)]",
  green: "bg-[var(--green)]",
  orange: "bg-[var(--orange)]",
} as const;

export function Waveform({ level, active = false, tone = "blue" }: WaveformProps): ReactNode {
  const energy = active ? Math.min(1, Math.max(0.12, level * 10)) : 0.14;
  return (
    <div className="flex h-7 items-end gap-[3px]" aria-hidden="true">
      {BARS.map((bar, index) => (
        <span
          key={index}
          className={`w-[3px] origin-bottom rounded-full ${toneColor[tone]}`}
          style={{
            height: `${Math.max(16, bar * energy * 100)}%`,
            opacity: 0.35 + energy * 0.65,
            transitionProperty: "height, opacity",
            transitionDuration: "120ms",
            transitionTimingFunction: "ease-out",
          }}
        />
      ))}
    </div>
  );
}
