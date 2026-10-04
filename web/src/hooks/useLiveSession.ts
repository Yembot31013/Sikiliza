import { useCallback, useEffect, useRef, useState } from "react";
import { captureMic, captureTab, startPcmPump, stopStream } from "../audio/capture";
import type {
  Caption,
  CaptionActivity,
  ConnectStep,
  HealthInfo,
  ServerEvent,
  SessionPhase,
  SourceMode,
} from "../types";

const WS_PATH = "/ws";

export function useLiveSession() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [phase, setPhase] = useState<SessionPhase>("idle");
  const [connectStep, setConnectStep] = useState<ConnectStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [speaking, setSpeaking] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [level, setLevel] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [source, setSource] = useState<SourceMode>("tab");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [provider, setProvider] = useState<string>("");
  const [hasVideo, setHasVideo] = useState(false);
  const [detectedLanguage, setDetectedLanguage] = useState("");
  const [revisedFlash, setRevisedFlash] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const stopPumpRef = useRef<(() => Promise<void>) | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startedAtRef = useRef<number>(0);
  const timerRef = useRef<number>(0);
  const pausedRef = useRef(false);
  const sendPausedRef = useRef(false);
  const intentionalCloseRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;

    const loadHealth = async () => {
      try {
        const response = await fetch("/health");
        if (!response.ok) {
          throw new Error("Caption server is not running.");
        }
        const info = (await response.json()) as HealthInfo;
        if (cancelled) return;
        setHealth(info);
        setError((current) =>
          current && current.includes("caption server") ? null : current,
        );
      } catch {
        if (cancelled) return;
        setHealth(null);
        timer = window.setTimeout(() => {
          void loadHealth();
        }, 1500);
      }
    };

    void loadHealth();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const clearLiveSignals = useCallback(() => {
    window.clearInterval(timerRef.current);
    setSpeaking(false);
    setProcessing(false);
    setLevel(0);
  }, []);

  const stopTransport = useCallback(async () => {
    clearLiveSignals();
    sendPausedRef.current = false;
    pausedRef.current = false;
    intentionalCloseRef.current = true;
    const socket = socketRef.current;
    socketRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify({ type: "stop" }));
      } catch {
        // Socket may already be half-closed.
      }
      socket.close();
    } else if (socket) {
      socket.close();
    }
    if (stopPumpRef.current) {
      await stopPumpRef.current();
      stopPumpRef.current = null;
    }
  }, [clearLiveSignals]);

  const teardown = useCallback(async () => {
    await stopTransport();
    if (streamRef.current) {
      stopStream(streamRef.current);
      streamRef.current = null;
    }
    setStream(null);
    setHasVideo(false);
    setElapsedMs(0);
    setConnectStep("idle");
    setPhase("idle");
    setCaptions([]);
    setDetectedLanguage("");
    setRevisedFlash(false);
    setProvider("");
  }, [stopTransport]);

  useEffect(() => {
    return () => {
      void teardown();
    };
  }, [teardown]);

  const attachTrackWatchers = useCallback(
    (media: MediaStream) => {
      media.getTracks().forEach((track) => {
        track.addEventListener("ended", () => {
          setError("The shared tab closed or stopped sharing.");
          setPhase("error");
          setConnectStep("idle");
          void stopTransport();
          if (streamRef.current) {
            stopStream(streamRef.current);
            streamRef.current = null;
          }
          setStream(null);
          setHasVideo(false);
        });
      });
    },
    [stopTransport],
  );

  const handleEvent = useCallback((event: ServerEvent) => {
    if (event.type === "ready") {
      setProvider(event.provider);
      setConnectStep("live");
      setPhase((current) => (current === "paused" ? "paused" : "live"));
      return;
    }
    if (event.type === "status") {
      if (sendPausedRef.current) return;
      if (typeof event.speaking === "boolean") {
        setSpeaking(event.speaking);
      }
      if (typeof event.processing === "boolean") {
        setProcessing(event.processing);
      }
      return;
    }
    if (event.type === "error") {
      setProcessing(false);
      setSpeaking(false);
      setError(event.message);
      const soft =
        event.soft === true ||
        event.code === "TRANSCRIBE_FAILED" ||
        event.code === "BAD_MESSAGE";
      if (soft) {
        window.setTimeout(() => {
          setError((current) => (current === event.message ? null : current));
        }, 4500);
        return;
      }
      setPhase((current) =>
        current === "live" || current === "connecting" || current === "paused"
          ? "error"
          : current,
      );
      return;
    }
    if (event.type === "final") {
      if (sendPausedRef.current) return;
      setProcessing(false);
      setSpeaking(false);
      if (event.language) {
        setDetectedLanguage(event.language);
      }
      setCaptions((current) => {
        if (event.kind === "update" && current.length > 0) {
          const next = [...current];
          const last = next[next.length - 1];
          if (last) {
            const revised =
              Boolean(event.revised) &&
              Boolean(last.translation) &&
              last.translation !== event.translation;
            if (revised) {
              setRevisedFlash(true);
              window.setTimeout(() => setRevisedFlash(false), 1800);
            }
            next[next.length - 1] = {
              ...last,
              source: event.source,
              translation: event.translation,
              language: event.language || last.language,
              endMs: event.endMs,
              revised,
            };
            return next;
          }
        }
        const next = [
          ...current,
          {
            id: event.id,
            kind: event.kind,
            source: event.source,
            translation: event.translation,
            language: event.language,
            startMs: event.startMs,
            endMs: event.endMs,
            revised: false,
          },
        ];
        return next.length > 100 ? next.slice(-100) : next;
      });
    }
  }, []);

  const sendConfig = useCallback((targetLanguage: string) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "config", targetLanguage }));
    }
  }, []);

  const beginTransport = useCallback(
    async (media: MediaStream) => {
      setConnectStep("warming_translation");
      setPhase("connecting");
      intentionalCloseRef.current = false;
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}${WS_PATH}`);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;

      await waitForOpen(socket);

      stopPumpRef.current = await startPcmPump(
        media,
        (bytes) => {
          if (sendPausedRef.current) return;
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(bytes);
          }
        },
        (nextLevel) => {
          if (!sendPausedRef.current) {
            setLevel(nextLevel);
          }
        },
      );

      socket.addEventListener("message", (message) => {
        try {
          handleEvent(JSON.parse(message.data as string) as ServerEvent);
        } catch {
          setError("Received a broken caption event.");
        }
      });
      socket.addEventListener("close", () => {
        if (socketRef.current === socket) {
          socketRef.current = null;
        }
        clearLiveSignals();

        if (intentionalCloseRef.current) {
          intentionalCloseRef.current = false;
          return;
        }

        void (async () => {
          if (stopPumpRef.current) {
            await stopPumpRef.current();
            stopPumpRef.current = null;
          }
        })();

        if (!streamRef.current) return;
        setPhase("error");
        setError("Caption connection dropped. Start again to resume.");
        setConnectStep((current) =>
          current === "warming_translation" || current === "capturing_audio"
            ? current
            : "idle",
        );
      });

      startedAtRef.current = Date.now();
      timerRef.current = window.setInterval(() => {
        if (!pausedRef.current) {
          setElapsedMs(Date.now() - startedAtRef.current);
        }
      }, 250);
    },
    [clearLiveSignals, handleEvent],
  );

  const releaseStream = useCallback(async () => {
    await stopTransport();
    if (streamRef.current) {
      stopStream(streamRef.current);
      streamRef.current = null;
    }
    setStream(null);
    setHasVideo(false);
  }, [stopTransport]);

  const linkTab = useCallback(async () => {
    setError(null);
    setSource("tab");
    setPhase("linking");
    setConnectStep("requesting_tab");
    let failedAt: ConnectStep = "requesting_tab";
    try {
      await releaseStream();
      const media = await captureTab();
      failedAt = "capturing_audio";
      setConnectStep("capturing_audio");
      streamRef.current = media;
      setStream(media);
      setHasVideo(media.getVideoTracks().length > 0);
      attachTrackWatchers(media);
      setPhase("linked");
      setConnectStep("idle");
    } catch (reason) {
      await teardown();
      setPhase("error");
      setConnectStep(failedAt);
      setError(reason instanceof Error ? reason.message : "Could not link that tab.");
    }
  }, [attachTrackWatchers, releaseStream, teardown]);

  const linkMic = useCallback(async () => {
    setError(null);
    setSource("mic");
    setPhase("linking");
    setConnectStep("requesting_tab");
    let failedAt: ConnectStep = "requesting_tab";
    try {
      await releaseStream();
      const media = await captureMic();
      failedAt = "capturing_audio";
      streamRef.current = media;
      setStream(media);
      setHasVideo(false);
      attachTrackWatchers(media);
      setPhase("linked");
      setConnectStep("idle");
    } catch (reason) {
      await teardown();
      setPhase("error");
      setConnectStep(failedAt);
      setError(reason instanceof Error ? reason.message : "Could not open the microphone.");
    }
  }, [attachTrackWatchers, releaseStream, teardown]);

  const startTranslation = useCallback(async (targetLanguage = "en") => {
    const media = streamRef.current;
    if (!media) {
      setError("Link a tab before starting translation.");
      setPhase("error");
      return;
    }
    setError(null);
    setCaptions([]);
    setDetectedLanguage("");
    setRevisedFlash(false);
    sendPausedRef.current = false;
    pausedRef.current = false;
    try {
      await beginTransport(media);
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({ type: "config", targetLanguage }),
        );
      }
      setPhase("live");
    } catch (reason) {
      setPhase("error");
      setError(reason instanceof Error ? reason.message : "Could not start translation.");
      // Keep warming_translation so the roadmap can mark where it failed.
    }
  }, [beginTransport]);

  const pause = useCallback(() => {
    if (phase !== "live") return;
    pausedRef.current = true;
    sendPausedRef.current = true;
    setSpeaking(false);
    setProcessing(false);
    setPhase("paused");
  }, [phase]);

  const resume = useCallback(() => {
    if (phase !== "paused") return;
    pausedRef.current = false;
    sendPausedRef.current = false;
    startedAtRef.current = Date.now() - elapsedMs;
    setPhase("live");
  }, [elapsedMs, phase]);

  const stop = useCallback(async () => {
    await teardown();
  }, [teardown]);

  const disconnect = useCallback(async () => {
    await teardown();
  }, [teardown]);

  const clearCaptions = useCallback(() => {
    setCaptions([]);
    setDetectedLanguage("");
    setRevisedFlash(false);
  }, []);

  const retry = useCallback(async () => {
    setError(null);
    if (streamRef.current && (phase === "error" || phase === "linked")) {
      await startTranslation();
      return;
    }
    await linkTab();
  }, [linkTab, phase, startTranslation]);

  const active = captions[captions.length - 1] ?? null;
  // Activity must reflect server status only — local audio level is not proof
  // that captions are being produced (and stays high after a dropped socket).
  const activity: CaptionActivity =
    phase === "live"
      ? processing
        ? "translating"
        : speaking
          ? "hearing"
          : "waiting"
      : "waiting";

  return {
    health,
    phase,
    connectStep,
    error,
    captions,
    active,
    speaking,
    processing,
    activity,
    level,
    elapsedMs,
    source,
    stream,
    hasVideo,
    provider,
    detectedLanguage,
    revisedFlash,
    linkTab,
    linkMic,
    startTranslation,
    pause,
    resume,
    stop,
    disconnect,
    clearCaptions,
    retry,
    sendConfig,
  };
}

function waitForOpen(socket: WebSocket): Promise<void> {
  if (socket.readyState === WebSocket.OPEN) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const onOpen = () => {
      cleanup();
      resolve();
    };
    const onError = () => {
      cleanup();
      reject(new Error("Could not connect to the caption server."));
    };
    const cleanup = () => {
      socket.removeEventListener("open", onOpen);
      socket.removeEventListener("error", onError);
    };
    socket.addEventListener("open", onOpen);
    socket.addEventListener("error", onError);
  });
}
