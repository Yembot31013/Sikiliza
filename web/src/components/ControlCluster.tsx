import type { CaptionPrefs } from "../types";
import { Button } from "./ui/Button";
import { Select } from "./ui/Select";

type ControlClusterProps = {
  prefs: CaptionPrefs;
  onChange: (next: CaptionPrefs) => void;
  mobileOpen: boolean;
  onToggleMobile: () => void;
};

const TARGET_OPTIONS = [
  { value: "en", label: "English" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "sw", label: "Swahili" },
  { value: "de", label: "German" },
  { value: "pt", label: "Portuguese" },
];

const SIZE_OPTIONS = [
  { value: "sm", label: "Small" },
  { value: "md", label: "Medium" },
  { value: "lg", label: "Large" },
];

export function ControlCluster({
  prefs,
  onChange,
  mobileOpen,
  onToggleMobile,
}: ControlClusterProps) {
  return (
    <div className="pointer-events-auto relative z-50">
      <button
        type="button"
        className="label-mono mb-2 inline-flex min-h-10 items-center rounded-full border border-white/70 bg-white/80 px-3 lg:hidden"
        onClick={onToggleMobile}
      >
        {mobileOpen ? "Hide controls" : "Controls"}
      </button>

      <div
        className={`panel-glass flex flex-wrap items-center gap-2 rounded-[var(--radius-22)] p-2 ${
          mobileOpen ? "flex" : "hidden lg:flex"
        }`}
      >
        <Select
          label="Target"
          value={prefs.targetLanguage}
          options={TARGET_OPTIONS}
          onChange={(targetLanguage) => onChange({ ...prefs, targetLanguage })}
        />
        <Select
          label="Size"
          value={prefs.captionSize}
          options={SIZE_OPTIONS}
          onChange={(captionSize) =>
            onChange({
              ...prefs,
              captionSize: captionSize as CaptionPrefs["captionSize"],
            })
          }
        />

        <ToggleChip
          active={prefs.showSource}
          label="Source"
          onClick={() => onChange({ ...prefs, showSource: !prefs.showSource })}
        />
        <ToggleChip
          active={prefs.showTranslation}
          label="Translation"
          onClick={() =>
            onChange({ ...prefs, showTranslation: !prefs.showTranslation })
          }
        />
        <ToggleChip
          active={prefs.dockCollapsed}
          label="One line"
          onClick={() =>
            onChange({ ...prefs, dockCollapsed: !prefs.dockCollapsed })
          }
        />
        <ToggleChip
          active={prefs.dockPinned}
          label="Pin dock"
          onClick={() => onChange({ ...prefs, dockPinned: !prefs.dockPinned })}
        />
        <Button
          variant="ghost"
          className="min-h-9 px-3 text-xs"
          onClick={() =>
            onChange({
              ...prefs,
              objectFit: prefs.objectFit === "contain" ? "cover" : "contain",
            })
          }
        >
          {prefs.objectFit === "contain" ? "Fill" : "Fit"}
        </Button>
      </div>
    </div>
  );
}

function ToggleChip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-9 rounded-full border px-3 text-[11px] font-semibold transition-colors duration-150 ${
        active
          ? "border-[color-mix(in_srgb,var(--blue)_40%,transparent)] bg-[color-mix(in_srgb,var(--blue)_16%,white)] text-[var(--ink)]"
          : "border-[color-mix(in_srgb,var(--ink)_12%,transparent)] bg-white/70 text-[var(--muted)]"
      }`}
    >
      {label}
    </button>
  );
}
