import type { ReactNode } from "react";

export function PageHeader({ title, lede, actions }: { title: string; lede?: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 className="text-[28px] font-semibold leading-none">{title}</h1>
        {lede && <p className="mt-2 text-[15px] text-muted">{lede}</p>}
      </div>
      {actions}
    </header>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="card px-6 py-10 text-center text-[15px] text-muted">{children}</div>;
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const msg = error instanceof Error ? error.message : String(error);
  return <div className="rounded-card border border-stamp/30 bg-stamp-wash px-3 py-2 text-[14px] text-stamp">{msg}</div>;
}

export function Tag({ children }: { children: ReactNode }) {
  return <span className="rounded-sm border border-line bg-paper px-1.5 py-0.5 font-mono text-[11px] text-ink-soft">{children}</span>;
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
