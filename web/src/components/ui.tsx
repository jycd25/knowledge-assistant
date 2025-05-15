import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

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

/** Category → topic picker used by search scope, import, notes and entry editing. */
export function ScopePicker({ categoryId, topicId, onChange, allowNone = true }:
  { categoryId: string | null; topicId: string | null; onChange: (c: string | null, t: string | null) => void; allowNone?: boolean }) {
  const cats = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const topics = useQuery({ queryKey: ["topics", categoryId], queryFn: () => api.topics(categoryId!), enabled: !!categoryId });
  return (
    <div className="flex flex-wrap gap-2">
      <select className="field w-auto" value={categoryId ?? ""} onChange={(e) => onChange(e.target.value || null, null)}>
        <option value="">{allowNone ? "Any category" : "Choose a category"}</option>
        {cats.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <select className="field w-auto" value={topicId ?? ""} disabled={!categoryId} onChange={(e) => onChange(categoryId, e.target.value || null)}>
        <option value="">{allowNone ? "Any topic" : "Choose a topic"}</option>
        {topics.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select>
    </div>
  );
}

export function fmtDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
