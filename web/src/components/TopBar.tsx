import { formatElapsed, providerLabel } from "../lib/labels";
import type { CaptionActivity, SessionPhase } from "../types";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { Waveform } from "./Waveform";

type TopBarProps = {
  phase: SessionPhase;
  activity: CaptionActivity;
  level: number;
  configured: boolean;
  serverDown: boolean;
  elapsedMs: number;
  provider: string;
  languagePair: string;
  onLink: () => void;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  onToggleHistory: () => void;
  historyOpen: boolean;
};

function statusBadge(phase: SessionPhase, activity: CaptionActivity) {
  if (phase === "live" && activity === "translating") {
    return (
      <Badge tone="ok" pulse>
        Translating
      </Badge>
    );
  }
  if (phase === "live" && activity === "hearing") {
    return (
      <Badge tone="info" pulse>
        Hearing
      </Badge>
    );
  }
  if (phase === "live") {
    return <Badge tone="live">Live</Badge>;
  }
  if (phase === "paused") {
    return <Badge tone="warn">Paused</Badge>;
  }
  if (phase === "linking" || phase === "connecting") {
    return (
      <Badge tone="info" pulse>
        Connecting
      </Badge>
    );
  }
  if (phase === "linked") {
    return <Badge tone="ok">Linked · Waiting</Badge>;
  }
  if (phase === "error") {
    return <Badge tone="pink">Needs attention</Badge>;
  }
  return <Badge>Standby</Badge>;
}

export function TopBar({
  phase,
  activity,
  level,
  configured,
  serverDown,
  elapsedMs,
  provider,
  languagePair,
  onLink,
  onStart,
  onStop,
  onPause,
  onResume,
  onToggleHistory,
  historyOpen,
}: TopBarProps) {
  const canStart = phase === "linked" && configured && !serverDown;
  const liveLike = phase === "live" || phase === "paused";

  return (
    <header className="sticky top-0 z-30 shrink-0 px-3 pt-3 sm:px-5">
      <div className="panel-glass mx-auto flex max-w-[1600px] flex-wrap items-center gap-3 rounded-[var(--radius-44)] px-4 py-3 sm:px-5">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <p className="truncate text-lg font-bold tracking-tight text-[var(--ink)]">Sikiliza</p>
          {statusBadge(phase, activity)}
          {phase === "live" ? (
            <Waveform
              level={level}
              active={activity !== "waiting"}
              tone={activity === "translating" ? "orange" : "blue"}
            />
          ) : null}
          <span className="label-mono hidden md:inline">{languagePair}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="label-mono tabular-nums">{formatElapsed(elapsedMs)}</span>
          {provider ? (
            <span className="label-mono hidden lg:inline">{providerLabel(provider)}</span>
          ) : null}

          {phase === "idle" || phase === "error" ? (
            <Button onClick={onLink} disabled={serverDown || !configured}>
              Link tab
            </Button>
          ) : null}

          {phase === "linked" ? (
            <Button onClick={onStart} disabled={!canStart}>
              Start
            </Button>
          ) : null}

          {phase === "live" ? (
            <Button variant="ghost" onClick={onPause}>
              Pause
            </Button>
          ) : null}

          {phase === "paused" ? <Button onClick={onResume}>Resume</Button> : null}

          {liveLike || phase === "linked" || phase === "connecting" || phase === "linking" ? (
            <Button variant="secondary" onClick={onStop}>
              Stop
            </Button>
          ) : null}

          <Button variant="ghost" onClick={onToggleHistory} className="hidden sm:inline-flex">
            {historyOpen ? "Hide history" : "History"}
          </Button>
        </div>
      </div>
    </header>
  );
}
