import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { CaptionDock } from "./CaptionDock";

afterEach(() => {
  cleanup();
});

describe("CaptionDock", () => {
  const prefs = {
    showSource: true,
    showTranslation: true,
    captionSize: "md" as const,
    objectFit: "contain" as const,
    dockCollapsed: false,
    dockPinned: true,
    historyOpen: false,
    targetLanguage: "en",
  };

  it("renders translation as the primary caption over the stage", () => {
    render(
      <CaptionDock
        phase="live"
        activity="waiting"
        level={0}
        prefs={prefs}
        caption={{
          id: 1,
          kind: "new",
          source: "Nakupenda",
          translation: "I love you",
          startMs: 0,
          endMs: 1200,
        }}
      />,
    );
    expect(screen.getByText("I love you")).toBeInTheDocument();
    expect(screen.getByText("Nakupenda")).toBeInTheDocument();
  });

  it("shows hearing copy while speech is detected", () => {
    render(
      <CaptionDock
        caption={null}
        phase="live"
        activity="hearing"
        level={0.2}
        prefs={prefs}
      />,
    );
    expect(screen.getByText("Hearing speech…")).toBeInTheDocument();
    expect(screen.getByText("Hearing")).toBeInTheDocument();
  });

  it("hides leftover captions while linked and waiting", () => {
    const { container } = render(
      <CaptionDock
        phase="linked"
        activity="waiting"
        level={0}
        prefs={prefs}
        caption={{
          id: 1,
          kind: "new",
          source: "Sisi ni watu sana.",
          translation: "We are many people.",
          language: "sw",
          startMs: 0,
          endMs: 1200,
        }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows detected language and corrected badge while live", () => {
    render(
      <CaptionDock
        phase="live"
        activity="waiting"
        level={0}
        prefs={prefs}
        revised
        caption={{
          id: 1,
          kind: "update",
          source: "La nuit",
          translation: "The night.",
          language: "fr",
          startMs: 0,
          endMs: 900,
        }}
      />,
    );
    expect(screen.getByText("FR")).toBeInTheDocument();
    expect(screen.getByText("Corrected")).toBeInTheDocument();
    expect(screen.getByText("The night.")).toBeInTheDocument();
  });

  it("shows translating copy while the provider works", () => {
    render(
      <CaptionDock
        caption={null}
        phase="live"
        activity="translating"
        level={0.1}
        prefs={prefs}
      />,
    );
    expect(screen.getByText("Translating that moment…")).toBeInTheDocument();
  });

  it("marks the last caption as disconnected instead of hearing", () => {
    render(
      <CaptionDock
        phase="error"
        activity="waiting"
        level={0.4}
        prefs={prefs}
        caption={{
          id: 2,
          kind: "new",
          source: "Papa va venir avec moi",
          translation: "Dad is going to go with me.",
          startMs: 0,
          endMs: 2000,
        }}
      />,
    );
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
    expect(screen.queryByText("Hearing")).not.toBeInTheDocument();
    expect(screen.getByText("Dad is going to go with me.")).toBeInTheDocument();
    expect(
      screen.getByText("Caption stream stopped. Last line is kept for reference."),
    ).toBeInTheDocument();
  });
});
