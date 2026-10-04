import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

const styles: Record<Variant, string> = {
  primary:
    "bg-[var(--yellow)] text-[var(--ink)] shadow-[var(--shadow-soft)] hover:brightness-[1.02]",
  secondary: "bg-[var(--ink)] text-[var(--cream)] hover:bg-[#1f1f1f]",
  ghost:
    "bg-transparent text-[var(--ink)] border border-[color-mix(in_srgb,var(--ink)_18%,transparent)] hover:bg-white/50",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`btn-press inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold transition-[transform,background-color,filter,opacity] duration-150 disabled:pointer-events-none disabled:opacity-40 ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
