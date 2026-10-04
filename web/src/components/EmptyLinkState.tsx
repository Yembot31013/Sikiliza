import { Button } from "./ui/Button";
import { Panel } from "./ui/Panel";

type EmptyLinkStateProps = {
  configured: boolean;
  serverDown: boolean;
  error: string | null;
  onLink: () => void;
  onMic?: () => void;
};

export function EmptyLinkState({
  configured,
  serverDown,
  error,
  onLink,
  onMic,
}: EmptyLinkStateProps) {
  return (
    <div className="relative flex h-full items-center justify-center overflow-hidden px-4 py-10">
      <span className="blob left-[-40px] top-10 h-52 w-52 bg-[var(--yellow)]" />
      <span className="blob bottom-8 right-[-20px] h-56 w-56 bg-[var(--pink)]" />
      <span className="blob right-1/3 top-1/4 h-40 w-40 bg-[var(--blue)]" />

      <Panel className="fade-in relative z-10 w-full max-w-xl">
        <p className="label-mono text-[var(--orange)]">Watch here · translate with it</p>
        <h1 className="mt-3 text-balance text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          Link a tab to begin
        </h1>
        <ol className="mt-6 space-y-3 text-sm leading-6 text-[var(--muted)]">
          <li className="grid grid-cols-[2.2rem_1fr] gap-2">
            <span className="label-mono text-[var(--ink)]">01</span>
            <span>Choose the Chrome tab with your live</span>
          </li>
          <li className="grid grid-cols-[2.2rem_1fr] gap-2">
            <span className="label-mono text-[var(--ink)]">02</span>
            <span>Allow tab audio when Chrome asks</span>
          </li>
          <li className="grid grid-cols-[2.2rem_1fr] gap-2">
            <span className="label-mono text-[var(--ink)]">03</span>
            <span>Start translation — captions float on the shared screen</span>
          </li>
        </ol>

        <div className="mt-7 flex flex-wrap gap-3">
          <Button onClick={onLink} disabled={serverDown || !configured}>
            Link tab
          </Button>
          {onMic ? (
            <Button variant="ghost" onClick={onMic} disabled={serverDown || !configured}>
              Use mic instead
            </Button>
          ) : null}
        </div>

        {serverDown ? (
          <p className="mt-5 rounded-[var(--radius-22)] border border-[color-mix(in_srgb,var(--orange)_35%,transparent)] bg-[color-mix(in_srgb,var(--orange)_12%,white)] px-4 py-3 text-sm leading-6" role="alert">
            Caption server offline. Run <code className="font-[var(--font-mono)] text-[12px]">./scripts/dev.sh</code>
          </p>
        ) : null}

        {!serverDown && !configured ? (
          <p className="mt-5 rounded-[var(--radius-22)] border border-[color-mix(in_srgb,var(--yellow)_40%,transparent)] bg-[color-mix(in_srgb,var(--yellow)_16%,white)] px-4 py-3 text-sm leading-6" role="status">
            Add <code className="font-[var(--font-mono)] text-[12px]">INTRON_API_KEY</code>,{" "}
            <code className="font-[var(--font-mono)] text-[12px]">GEMINI_API_KEY</code>, or{" "}
            <code className="font-[var(--font-mono)] text-[12px]">GROQ_API_KEY</code> to{" "}
            <code className="font-[var(--font-mono)] text-[12px]">.env</code>, then restart.
          </p>
        ) : null}

        {error ? (
          <p className="mt-4 text-sm leading-6 text-[var(--orange)]" role="alert">
            {error}
          </p>
        ) : null}
      </Panel>
    </div>
  );
}
