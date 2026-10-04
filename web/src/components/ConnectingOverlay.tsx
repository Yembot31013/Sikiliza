import type { ConnectStep } from "../types";
import { Panel } from "./ui/Panel";

const STEPS: { id: ConnectStep; label: string; hint: string }[] = [
  {
    id: "requesting_tab",
    label: "Requesting tab access",
    hint: "Chrome share dialog",
  },
  {
    id: "capturing_audio",
    label: "Capturing audio",
    hint: "Tab audio stream",
  },
  {
    id: "warming_translation",
    label: "Warming translation",
    hint: "Opening caption channel",
  },
  {
    id: "live",
    label: "Go live",
    hint: "Captions ready",
  },
];

export type RoadmapStatus = "pending" | "loading" | "done" | "failed";

type ConnectingOverlayProps = {
  step: ConnectStep;
  failed?: boolean;
  title?: string;
};

export function stepStatus(
  stepId: ConnectStep,
  activeStep: ConnectStep,
  failed = false,
): RoadmapStatus {
  const order = STEPS.map((item) => item.id);
  const activeIndex = Math.max(0, order.indexOf(activeStep));
  const index = order.indexOf(stepId);
  if (index < 0) return "pending";
  if (failed && index === activeIndex) return "failed";
  if (activeStep === "live" && index <= activeIndex) return "done";
  if (index < activeIndex) return "done";
  if (index === activeIndex) return "loading";
  return "pending";
}

function statusCopy(status: RoadmapStatus): string {
  if (status === "done") return "Connected";
  if (status === "loading") return "In progress";
  if (status === "failed") return "Failed";
  return "Pending";
}

export function ConnectingOverlay({
  step,
  failed = false,
  title = "Getting ready",
}: ConnectingOverlayProps) {
  const activeIndex = Math.max(
    0,
    STEPS.findIndex((item) => item.id === step),
  );
  const progress = failed
    ? ((activeIndex + 0.35) / STEPS.length) * 100
    : step === "live"
      ? 100
      : ((activeIndex + 0.55) / STEPS.length) * 100;

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-[color-mix(in_srgb,var(--cream)_42%,transparent)] px-4 backdrop-blur-[2px]">
      <Panel className="fade-in w-full max-w-md">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="label-mono text-[var(--blue)]">{title}</p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {failed
                ? "Something stopped along the way."
                : "Following the link path to live captions."}
            </p>
          </div>
          <span className="label-mono shrink-0 rounded-full bg-white/80 px-2.5 py-1 text-[var(--ink)]">
            {Math.min(activeIndex + 1, STEPS.length)}/{STEPS.length}
          </span>
        </div>

        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/80">
          <div
            className={`h-full rounded-full transition-[width] duration-500 ease-out ${
              failed ? "bg-[var(--orange)]" : "progress-bar"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        <ol className="mt-6 space-y-0" aria-label="Connection progress">
          {STEPS.map((item, index) => {
            const status = stepStatus(item.id, step, failed);
            const isLast = index === STEPS.length - 1;
            return (
              <li key={item.id} className="relative flex gap-3">
                <div className="flex w-7 shrink-0 flex-col items-center">
                  <StepMarker status={status} />
                  {!isLast ? (
                    <div
                      className={`mt-1 w-0.5 flex-1 min-h-6 rounded-full ${
                        status === "done"
                          ? "bg-[color-mix(in_srgb,var(--green)_55%,white)]"
                          : status === "failed"
                            ? "bg-[color-mix(in_srgb,var(--orange)_40%,white)]"
                            : "bg-[color-mix(in_srgb,var(--ink)_12%,white)]"
                      }`}
                      aria-hidden="true"
                    />
                  ) : null}
                </div>

                <div className={`min-w-0 flex-1 pb-5 ${isLast ? "pb-0" : ""}`}>
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                    <p
                      className={`text-sm font-semibold leading-5 ${
                        status === "pending"
                          ? "text-[var(--muted)]"
                          : status === "failed"
                            ? "text-[var(--ink)]"
                            : "text-[var(--ink)]"
                      }`}
                    >
                      {item.label}
                    </p>
                    <span
                      className={`label-mono ${
                        status === "done"
                          ? "text-[color-mix(in_srgb,var(--green)_70%,var(--ink))]"
                          : status === "loading"
                            ? "text-[color-mix(in_srgb,var(--blue)_75%,var(--ink))]"
                            : status === "failed"
                              ? "text-[color-mix(in_srgb,var(--orange)_80%,var(--ink))]"
                              : "text-[var(--muted)]"
                      }`}
                    >
                      {statusCopy(status)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs leading-5 text-[var(--muted)]">
                    {item.hint}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      </Panel>
    </div>
  );
}

function StepMarker({ status }: { status: RoadmapStatus }) {
  if (status === "done") {
    return (
      <span
        className="flex h-7 w-7 items-center justify-center rounded-full border border-[color-mix(in_srgb,var(--green)_45%,transparent)] bg-[color-mix(in_srgb,var(--green)_22%,white)] text-[11px] font-bold text-[var(--ink)]"
        aria-hidden="true"
      >
        ✓
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span
        className="flex h-7 w-7 items-center justify-center rounded-full border border-[color-mix(in_srgb,var(--orange)_50%,transparent)] bg-[color-mix(in_srgb,var(--orange)_20%,white)] text-[11px] font-bold text-[var(--ink)]"
        aria-hidden="true"
      >
        !
      </span>
    );
  }

  if (status === "loading") {
    return (
      <span
        className="relative flex h-7 w-7 items-center justify-center rounded-full border border-[color-mix(in_srgb,var(--blue)_45%,transparent)] bg-[color-mix(in_srgb,var(--blue)_16%,white)]"
        aria-hidden="true"
      >
        <span className="absolute inset-0 animate-[soft-pulse_1.4s_ease-in-out_infinite] rounded-full border border-[color-mix(in_srgb,var(--blue)_35%,transparent)]" />
        <span className="h-2 w-2 rounded-full bg-[var(--blue)]" />
      </span>
    );
  }

  return (
    <span
      className="flex h-7 w-7 items-center justify-center rounded-full border border-[color-mix(in_srgb,var(--ink)_14%,transparent)] bg-white/80"
      aria-hidden="true"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-[color-mix(in_srgb,var(--ink)_22%,white)]" />
    </span>
  );
}
