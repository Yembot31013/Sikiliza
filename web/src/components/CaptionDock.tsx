import type { Caption, CaptionActivity, CaptionPrefs, SessionPhase } from "../types";
import { languageBadge } from "../lib/labels";
import { Badge } from "./ui/Badge";
import { Waveform } from "./Waveform";

type CaptionDockProps = {
  caption: Caption | null;
  phase: SessionPhase;
  activity: CaptionActivity;
  level: number;
  prefs: CaptionPrefs;
  revised?: boolean;
};

const sizeClass = {
  sm: "text-lg sm:text-xl",
  md: "text-xl sm:text-2xl",
  lg: "text-2xl sm:text-[1.85rem]",
} as const;

function activityCopy(activity: CaptionActivity, phase: SessionPhase): string {
  if (phase === "error") return "Connection lost — last caption kept.";
  if (phase === "paused") return "Captions paused.";
  if (activity === "translating") return "Translating that moment…";
  if (activity === "hearing") return "Hearing speech…";
  return "Waiting for speech…";
}

export function CaptionDock({
  caption,
  phase,
  activity,
  level,
  prefs,
  revised = false,
}: CaptionDockProps) {
  const live = phase === "live" || phase === "paused";
  const disconnected = phase === "error";
  // Never show leftover captions while linked/waiting — that reads as live truth.
  if (!live && !disconnected) return null;
  if (disconnected && !caption) return null;

  const placeholder = activityCopy(activity, phase);
  const translation = caption?.translation || placeholder;
  const source = caption?.source ?? "";
  const showWave = phase === "live" && (activity === "hearing" || activity === "translating");
  const detected = languageBadge(caption?.language);

  return (
    <section
      className="pointer-events-none absolute inset-x-0 bottom-0 z-10 px-3 pb-3 sm:px-5 sm:pb-5"
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        className={`mx-auto max-w-5xl rounded-[var(--radius-32)] border border-white/80 bg-[color-mix(in_srgb,var(--cream)_82%,white)] px-5 py-4 shadow-[var(--shadow-lift)] backdrop-blur-md sm:px-6 ${
          disconnected ? "opacity-90" : ""
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-3">
          {disconnected ? <Badge tone="warn">Disconnected</Badge> : null}
          {detected ? <Badge tone="neutral">{detected}</Badge> : null}
          {revised && phase === "live" ? <Badge tone="ok">Corrected</Badge> : null}
          {phase === "live" && activity === "hearing" ? (
            <Badge tone="info" pulse>
              Hearing
            </Badge>
          ) : null}
          {phase === "live" && activity === "translating" ? (
            <Badge tone="ok" pulse>
              Translating
            </Badge>
          ) : null}
          {phase === "live" && activity === "waiting" && !revised ? (
            <Badge tone="live">Live</Badge>
          ) : null}
          {phase === "paused" ? <Badge tone="warn">Paused</Badge> : null}
          {showWave ? (
            <Waveform
              level={level}
              active
              tone={activity === "translating" ? "orange" : "blue"}
            />
          ) : null}
        </div>

        {prefs.dockCollapsed ? (
          <p
            className={`font-semibold leading-snug text-[var(--ink)] text-pretty ${sizeClass[prefs.captionSize]}`}
          >
            {prefs.showTranslation ? translation : source || translation}
          </p>
        ) : (
          <>
            {prefs.showSource && source ? (
              <p className="mb-1.5 max-w-4xl text-sm leading-6 text-[var(--muted)] text-pretty">
                {source}
              </p>
            ) : null}
            {prefs.showTranslation ? (
              <p
                className={`font-semibold leading-snug text-[var(--ink)] text-pretty transition-colors duration-300 ${sizeClass[prefs.captionSize]} ${
                  !caption || disconnected ? "text-[var(--muted)]" : ""
                } ${revised ? "text-[color-mix(in_srgb,var(--blue)_35%,var(--ink))]" : ""}`}
              >
                {translation}
              </p>
            ) : null}
            {disconnected ? (
              <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
                Caption stream stopped. Last line is kept for reference.
              </p>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
