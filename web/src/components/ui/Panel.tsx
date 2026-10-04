import type { HTMLAttributes, ReactNode } from "react";

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  padded?: boolean;
};

export function Panel({ children, className = "", padded = true, ...rest }: PanelProps) {
  return (
    <div
      className={`panel-glass rounded-[var(--radius-32)] ${padded ? "p-6 sm:p-8" : ""} ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
