export type CaptionKind = "new" | "update";

export type Caption = {
  id: number;
  kind: CaptionKind;
  source: string;
  translation: string;
  language?: string;
  startMs: number;
  endMs: number;
  revised?: boolean;
};

export type HealthInfo = {
  ok: boolean;
  provider: "intron" | "gemini" | "groq" | "openai" | "local" | "auto";
  mode: "accurate" | "fast";
  configured: boolean;
};

export type SourceMode = "tab" | "mic";

export type SessionPhase =
  | "idle"
  | "linking"
  | "linked"
  | "connecting"
  | "live"
  | "paused"
  | "error";

export type ConnectStep =
  | "idle"
  | "requesting_tab"
  | "capturing_audio"
  | "warming_translation"
  | "live";

export type CaptionSize = "sm" | "md" | "lg";
export type ObjectFitMode = "contain" | "cover";

export type CaptionPrefs = {
  showSource: boolean;
  showTranslation: boolean;
  captionSize: CaptionSize;
  objectFit: ObjectFitMode;
  dockCollapsed: boolean;
  dockPinned: boolean;
  historyOpen: boolean;
  targetLanguage: string;
};

export type CaptionActivity = "waiting" | "hearing" | "translating";

export type ServerEvent =
  | {
      type: "ready";
      provider: HealthInfo["provider"];
      mode: HealthInfo["mode"];
      targetLanguage?: string;
    }
  | { type: "status"; speaking?: boolean; processing?: boolean }
  | {
      type: "final";
      id: number;
      kind: CaptionKind;
      source: string;
      translation: string;
      language?: string;
      startMs: number;
      endMs: number;
      revised?: boolean;
    }
  | { type: "error"; code: string; message: string; soft?: boolean };
