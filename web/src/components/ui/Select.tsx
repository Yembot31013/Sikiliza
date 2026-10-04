import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type SelectOption = {
  value: string;
  label: string;
};

type SelectProps = {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
};

type MenuCoords = {
  left: number;
  bottom: number;
  minWidth: number;
};

export function Select({ label, value, options, onChange }: SelectProps) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<MenuCoords | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const listId = useId();
  const selected = options.find((option) => option.value === value) ?? options[0];

  useLayoutEffect(() => {
    if (!open || !buttonRef.current) {
      setCoords(null);
      return;
    }

    const update = () => {
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;
      setCoords({
        left: rect.left,
        bottom: window.innerHeight - rect.top + 8,
        minWidth: Math.max(rect.width, 148),
      });
    };

    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target) || menuRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative z-50 flex items-center gap-2 px-1">
      <span className="label-mono">{label}</span>
      <button
        ref={buttonRef}
        type="button"
        className="inline-flex min-h-9 min-w-[7.5rem] items-center justify-between gap-2 rounded-full border border-[color-mix(in_srgb,var(--ink)_12%,transparent)] bg-white px-3 text-xs font-semibold text-[var(--ink)] transition-colors duration-150 hover:border-[color-mix(in_srgb,var(--blue)_35%,transparent)]"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((current) => !current)}
      >
        <span>{selected?.label ?? "Select"}</span>
        <span aria-hidden="true" className="text-[10px] text-[var(--muted)]">
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open && coords
        ? createPortal(
            <ul
              ref={menuRef}
              id={listId}
              role="listbox"
              style={{
                left: coords.left,
                bottom: coords.bottom,
                minWidth: coords.minWidth,
              }}
              className="fade-in fixed z-[80] overflow-hidden rounded-[var(--radius-22)] border border-white/80 bg-[color-mix(in_srgb,var(--white)_96%,var(--cream))] p-1 shadow-[var(--shadow-lift)]"
            >
              {options.map((option) => {
                const active = option.value === value;
                return (
                  <li key={option.value} role="option" aria-selected={active}>
                    <button
                      type="button"
                      className={`flex min-h-10 w-full items-center rounded-full px-3 text-left text-xs font-semibold transition-colors duration-150 ${
                        active
                          ? "bg-[color-mix(in_srgb,var(--yellow)_40%,white)] text-[var(--ink)]"
                          : "text-[var(--ink)] hover:bg-[color-mix(in_srgb,var(--blue)_12%,white)]"
                      }`}
                      onClick={() => {
                        onChange(option.value);
                        setOpen(false);
                      }}
                    >
                      {option.label}
                    </button>
                  </li>
                );
              })}
            </ul>,
            document.body,
          )
        : null}
    </div>
  );
}
