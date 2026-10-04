import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyLinkState } from "./EmptyLinkState";

describe("EmptyLinkState", () => {
  it("explains linking a tab before translation", () => {
    render(
      <EmptyLinkState
        configured
        serverDown={false}
        error={null}
        onLink={() => undefined}
      />,
    );
    expect(screen.getByRole("heading", { name: /Link a tab to begin/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Link tab/i })).toBeInTheDocument();
  });

  it("asks for an API key when the backend is unconfigured", () => {
    render(
      <EmptyLinkState
        configured={false}
        serverDown={false}
        error={null}
        onLink={() => undefined}
      />,
    );
    expect(screen.getByText(/INTRON_API_KEY/)).toBeInTheDocument();
    expect(screen.getByText(/GEMINI_API_KEY/)).toBeInTheDocument();
  });
});
