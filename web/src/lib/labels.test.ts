import { describe, expect, it } from "vitest";
import { formatElapsed, languagePairLabel, providerLabel } from "./labels";

describe("formatElapsed", () => {
  it("formats minutes and seconds with tabular width", () => {
    expect(formatElapsed(0)).toBe("00:00");
    expect(formatElapsed(65000)).toBe("01:05");
  });

  it("does not go negative", () => {
    expect(formatElapsed(-400)).toBe("00:00");
  });
});

describe("providerLabel", () => {
  it("names known providers", () => {
    expect(providerLabel("intron")).toBe("Intron STT");
    expect(providerLabel("gemini")).toBe("Gemini Transcribe");
    expect(providerLabel("groq")).toBe("Groq Whisper");
    expect(providerLabel("mystery")).toBe("Auto");
  });
});

describe("languagePairLabel", () => {
  it("shows auto detection into the target language", () => {
    expect(languagePairLabel("en")).toBe("Auto → EN");
  });

  it("shows detected source language when known", () => {
    expect(languagePairLabel("en", "fr")).toBe("FR → EN");
  });
});
