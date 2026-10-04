import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ConnectingOverlay, stepStatus } from "./ConnectingOverlay";

afterEach(() => {
  cleanup();
});

describe("stepStatus", () => {
  it("marks earlier steps done, current loading, later pending", () => {
    expect(stepStatus("requesting_tab", "warming_translation")).toBe("done");
    expect(stepStatus("capturing_audio", "warming_translation")).toBe("done");
    expect(stepStatus("warming_translation", "warming_translation")).toBe("loading");
    expect(stepStatus("live", "warming_translation")).toBe("pending");
  });

  it("marks the active step failed when the connect path breaks", () => {
    expect(stepStatus("capturing_audio", "capturing_audio", true)).toBe("failed");
    expect(stepStatus("requesting_tab", "capturing_audio", true)).toBe("done");
    expect(stepStatus("warming_translation", "capturing_audio", true)).toBe("pending");
  });

  it("treats live as fully connected", () => {
    expect(stepStatus("requesting_tab", "live")).toBe("done");
    expect(stepStatus("live", "live")).toBe("done");
  });
});

describe("ConnectingOverlay", () => {
  it("renders a roadmap with status labels instead of only chips", () => {
    render(<ConnectingOverlay step="warming_translation" />);
    expect(screen.getByLabelText("Connection progress")).toBeInTheDocument();
    expect(screen.getByText("Warming translation")).toBeInTheDocument();
    expect(screen.getAllByText("Connected").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("In progress")).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThanOrEqual(1);
  });

  it("surfaces failed state on the active step", () => {
    render(<ConnectingOverlay step="warming_translation" failed />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Something stopped along the way.")).toBeInTheDocument();
  });
});
