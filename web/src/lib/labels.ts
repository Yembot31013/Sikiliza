export function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function providerLabel(provider: string): string {
  if (provider === "intron") return "Intron STT";
  if (provider === "gemini") return "Gemini Transcribe";
  if (provider === "groq") return "Groq Whisper";
  if (provider === "openai") return "OpenAI Whisper";
  if (provider === "local") return "Local Whisper";
  return "Auto";
}

export function languagePairLabel(
  targetLanguage: string,
  detectedLanguage?: string,
): string {
  const target = targetLanguage.toUpperCase();
  const detected = detectedLanguage?.trim();
  if (detected) {
    return `${detected.toUpperCase()} → ${target}`;
  }
  return `Auto → ${target}`;
}

export function languageBadge(code?: string): string {
  const value = code?.trim();
  if (!value) return "";
  return value.toUpperCase();
}
