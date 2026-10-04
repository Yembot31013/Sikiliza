import { useEffect, useRef, type ReactNode } from "react";
import type { CaptionPrefs, ConnectStep, SessionPhase } from "../types";
import { ConnectingOverlay } from "./ConnectingOverlay";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";

type StageProps = {
  stream: MediaStream | null;
  hasVideo: boolean;
  phase: SessionPhase;
  connectStep: ConnectStep;
  prefs: CaptionPrefs;
  level: number;
  onStart: () => void;
  onChangeTab: () => void;
  onDisconnect: () => void;
  children?: ReactNode;
};

export function Stage({
  stream,
  hasVideo,
  phase,
  connectStep,
  prefs,
  level,
  onStart,
  onChangeTab,
  onDisconnect,
  children,
}: StageProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const showVideo = Boolean(stream && hasVideo);
  const connecting = phase === "linking" || phase === "connecting";
  const connectFailed =
    phase === "error" &&
    connectStep !== "idle" &&
    connectStep !== "live";
  const showConnectOverlay = connecting || connectFailed;

  useEffect(() => {
    const node = videoRef.current;
    if (!node) return;
    node.srcObject = stream;
    if (stream) {
      void node.play().catch(() => undefined);
    }
  }, [stream]);

  return (
    <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-[var(--radius-32)] bg-[color-mix(in_srgb,var(--white)_55%,var(--cream))] shadow-[var(--shadow-soft)]">
        {showVideo ? (
          <video
            ref={videoRef}
            className={`h-full w-full bg-[color-mix(in_srgb,var(--ink)_6%,var(--cream))] ${
              prefs.objectFit === "cover" ? "object-cover" : "object-contain"
            } ${phase === "paused" ? "opacity-80" : ""}`}
            muted
            playsInline
            autoPlay
            aria-label="Shared browser tab"
          />
        ) : (
          <div className="flex h-full min-h-[420px] items-center justify-center bg-[linear-gradient(160deg,color-mix(in_srgb,var(--yellow)_16%,white),color-mix(in_srgb,var(--blue)_12%,white))]">
            {phase === "linked" ? (
              <div className="fade-in mx-4 max-w-md rounded-[var(--radius-32)] border border-white/80 bg-white/80 p-6 text-center shadow-[var(--shadow-soft)]">
                <Badge tone="ok">Linked · Waiting</Badge>
                <h2 className="mt-4 text-2xl font-bold tracking-tight">Ready when you are</h2>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  The shared tab is connected. Start translation to float captions on this stage.
                </p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  <Button onClick={onStart}>Start</Button>
                  <Button variant="ghost" onClick={onChangeTab}>
                    Change tab
                  </Button>
                  <Button variant="secondary" onClick={onDisconnect}>
                    Disconnect
                  </Button>
                </div>
              </div>
            ) : (
              <div className="h-40 w-[70%] animate-pulse rounded-[var(--radius-22)] bg-white/50" />
            )}
          </div>
        )}

        {showVideo && phase === "linked" ? (
          <div className="absolute inset-x-0 top-4 z-10 flex justify-center px-4">
            <div className="panel-glass flex flex-wrap items-center gap-2 rounded-full px-3 py-2">
              <Badge tone="ok">Linked · Waiting</Badge>
              <Button className="min-h-10" onClick={onStart}>
                Start
              </Button>
              <Button variant="ghost" className="min-h-10" onClick={onChangeTab}>
                Change tab
              </Button>
              <Button variant="secondary" className="min-h-10" onClick={onDisconnect}>
                Disconnect
              </Button>
            </div>
          </div>
        ) : null}

        {showVideo ? (
          <div className="pointer-events-none absolute left-4 top-4 flex flex-col gap-1">
            <span className="label-mono rounded-full bg-white/75 px-2.5 py-1">
              Audio {Math.round(Math.min(level * 100, 99))}
            </span>
          </div>
        ) : null}

        {showConnectOverlay ? (
          <ConnectingOverlay step={connectStep} failed={connectFailed} />
        ) : null}
        {children}
      </div>
    </div>
  );
}
