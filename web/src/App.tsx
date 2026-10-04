import { useState } from "react";
import { CaptionDock } from "./components/CaptionDock";
import { ControlCluster } from "./components/ControlCluster";
import { EmptyLinkState } from "./components/EmptyLinkState";
import { ErrorBanner } from "./components/ErrorBanner";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { Stage } from "./components/Stage";
import { TopBar } from "./components/TopBar";
import { languagePairLabel } from "./lib/labels";
import { useLiveSession } from "./hooks/useLiveSession";
import type { CaptionPrefs } from "./types";

const DEFAULT_PREFS: CaptionPrefs = {
  showSource: true,
  showTranslation: true,
  captionSize: "md",
  objectFit: "contain",
  dockCollapsed: false,
  dockPinned: true,
  historyOpen: false,
  targetLanguage: "en",
};

export function App() {
  const session = useLiveSession();
  const [prefs, setPrefs] = useState<CaptionPrefs>(DEFAULT_PREFS);
  const [mobileControlsOpen, setMobileControlsOpen] = useState(false);
  const serverDown = session.health === null;
  const configured = session.health?.configured ?? false;
  const showEmpty = session.phase === "idle" || (session.phase === "error" && !session.stream);

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden bg-[var(--cream)]">
      <TopBar
        phase={session.phase}
        activity={session.activity}
        level={session.level}
        configured={configured}
        serverDown={serverDown}
        elapsedMs={session.elapsedMs}
        provider={session.provider || session.health?.provider || ""}
        languagePair={languagePairLabel(
          prefs.targetLanguage,
          session.phase === "live" || session.phase === "paused"
            ? session.detectedLanguage || session.active?.language
            : undefined,
        )}
        onLink={() => void session.linkTab()}
        onStart={() => void session.startTranslation(prefs.targetLanguage)}
        onStop={() => void session.stop()}
        onPause={session.pause}
        onResume={session.resume}
        onToggleHistory={() =>
          setPrefs((current) => ({ ...current, historyOpen: !current.historyOpen }))
        }
        historyOpen={prefs.historyOpen}
      />

      <div className="mx-auto flex min-h-0 w-full max-w-[1600px] flex-1 flex-col gap-3 overflow-hidden px-3 py-3 sm:px-5 sm:py-4 lg:flex-row">
        <main className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-hidden">
          {showEmpty ? (
            <div className="min-h-[70vh] flex-1 overflow-hidden rounded-[var(--radius-32)] bg-[color-mix(in_srgb,var(--white)_40%,var(--cream))] shadow-[var(--shadow-soft)]">
              <EmptyLinkState
                configured={configured}
                serverDown={serverDown}
                error={session.error}
                onLink={() => void session.linkTab()}
                onMic={() => void session.linkMic()}
              />
            </div>
          ) : (
            <Stage
              stream={session.stream}
              hasVideo={session.hasVideo}
              phase={session.phase}
              connectStep={session.connectStep}
              prefs={prefs}
              level={session.level}
              onStart={() => void session.startTranslation(prefs.targetLanguage)}
              onChangeTab={() => void session.linkTab()}
              onDisconnect={() => void session.disconnect()}
            >
              <CaptionDock
                caption={session.active}
                phase={session.phase}
                activity={session.activity}
                level={session.level}
                prefs={prefs}
                revised={session.revisedFlash}
              />
            </Stage>
          )}

          {!showEmpty ? (
            <div className="flex shrink-0 flex-wrap items-end justify-between gap-3">
              <ControlCluster
                prefs={prefs}
                onChange={(next) => {
                  if (next.targetLanguage !== prefs.targetLanguage) {
                    session.sendConfig(next.targetLanguage);
                  }
                  setPrefs(next);
                }}
                mobileOpen={mobileControlsOpen}
                onToggleMobile={() => setMobileControlsOpen((open) => !open)}
              />
            </div>
          ) : null}

          {session.error && !showEmpty ? (
            <div className="shrink-0">
              <ErrorBanner
                message={session.error}
                onRetry={() => void session.retry()}
              />
            </div>
          ) : null}
        </main>

        <HistoryDrawer
          open={prefs.historyOpen}
          captions={session.captions}
          onClose={() => setPrefs((current) => ({ ...current, historyOpen: false }))}
          onClear={session.clearCaptions}
        />
      </div>
    </div>
  );
}
