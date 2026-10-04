import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Select } from "./Select";

afterEach(() => {
  cleanup();
});

describe("Select", () => {
  it("portals the menu to document.body above other UI layers", () => {
    render(
      <Select
        label="Target"
        value="en"
        options={[
          { value: "en", label: "English" },
          { value: "fr", label: "French" },
        ]}
        onChange={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /English/i }));
    const list = screen.getByRole("listbox");
    expect(list.parentElement).toBe(document.body);
    expect(list.className).toContain("z-[80]");
    expect(screen.getByRole("option", { name: "French" })).toBeInTheDocument();
  });
});
