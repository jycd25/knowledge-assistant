import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import ReactMarkdown from "react-markdown";
import { Sparkles, Trash2, Wand2 } from "lucide-react";
import { api } from "../lib/api";
import type { Note } from "../lib/types";
import { Empty, ErrorNote, PageHeader, ScopePicker, Tag, fmtDate } from "../components/ui";

export default function NotesPage() {
  const qc = useQueryClient();
  const notes = useQuery({ queryKey: ["notes"], queryFn: api.notes });
  const templates = useQuery({ queryKey: ["templates"], queryFn: api.templates });
  const builtin = useQuery({ queryKey: ["templates", "builtin"], queryFn: api.builtinTemplates });
  const [selected, setSelected] = useState<Note | null>(null);
  const [body, setBody] = useState("");
  const [request, setRequest] = useState("");
  const [processed, setProcessed] = useState<{ markdown: string; title: string; tags: string[]; used_llm: boolean } | null>(null);
  const [cat, setCat] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const invalidate = () => qc.invalidateQueries({ queryKey: ["notes"] });

  const process = useMutation({ mutationFn: (use_llm: boolean) => api.processNote({ text: body, user_request: request || undefined, use_llm }), onSuccess: setProcessed });
  const save = useMutation({
    mutationFn: () => selected
      ? api.updateNote(selected.id, { body, processed_body: processed?.markdown ?? selected.processed_body, tags: processed?.tags ?? selected.tags, title: processed?.title ?? selected.title })
      : api.createNote({ body, title: processed?.title, tags: processed?.tags }).then((n) => processed ? api.updateNote(n.id, { processed_body: processed.markdown }) : n),
    onSuccess: (n) => { setSelected(n); void invalidate(); },
  });
  const del = useMutation({ mutationFn: (id: string) => api.deleteNote(id), onSuccess: () => { reset(); void invalidate(); } });
  const promote = useMutation({ mutationFn: () => api.noteToEntry(selected!.id, { topic_id: topic, use_processed: !!(processed ?? selected?.processed_body) }), onSuccess: () => { void invalidate(); void qc.invalidateQueries({ queryKey: ["entries"] }); } });

  function reset() { setSelected(null); setBody(""); setProcessed(null); setRequest(""); }
  function open(n: Note) { setSelected(n); setBody(n.body); setProcessed(n.processed_body ? { markdown: n.processed_body, title: n.title, tags: n.tags, used_llm: true } : null); }
  function useTemplate(text: string) { setBody((b) => (b.trim() ? b + "\n\n" : "") + text); }

  return (
    <div>
      <PageHeader title="Notes" lede="Write freely, then tidy it into a structured note and promote it to the library when it's worth keeping."
        actions={<button className="btn-quiet" onClick={reset}>New note</button>} />
      <div className="grid grid-cols-[220px_minmax(0,1fr)_minmax(0,1fr)] gap-5">
        <aside>
          <div className="eyebrow mb-2">saved notes</div>
          {notes.data?.length === 0 && <div className="text-[13px] text-muted">None yet.</div>}
          <ul className="flex flex-col gap-1">
            {notes.data?.map((n) => (
              <li key={n.id}>
                <button onClick={() => open(n)} className={`block w-full rounded-card px-2 py-1.5 text-left ${selected?.id === n.id ? "bg-accent-wash text-accent-ink" : "hover:bg-card"}`}>
                  <div className="truncate text-[14px] font-medium">{n.title}</div>
                  <div className="text-[11px] text-muted">{fmtDate(n.updated_at)}{n.entry_id && " · in library"}</div>
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="eyebrow">draft</div>
            <select className="field w-auto py-1 text-[13px]" defaultValue="" onChange={(e) => { const v = e.target.value; if (!v) return; const [kind, key] = v.split(":"); useTemplate(kind === "b" ? builtin.data![key] : templates.data!.find((t) => t.id === key)!.body); e.target.value = ""; }}>
              <option value="">Insert a template…</option>
              {builtin.data && Object.keys(builtin.data).map((k) => <option key={k} value={`b:${k}`}>{k}</option>)}
              {templates.data?.map((t) => <option key={t.id} value={`u:${t.id}`}>{t.name} (yours)</option>)}
            </select>
          </div>
          <textarea className="field min-h-80 font-mono text-[13px]" placeholder="Today I learned…" value={body} onChange={(e) => setBody(e.target.value)} />
          <input className="field" placeholder="Instructions for the AI pass (optional): “make it a checklist”, “keep it under 200 words”" value={request} onChange={(e) => setRequest(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={!body.trim() || process.isPending} onClick={() => process.mutate(true)}><Sparkles size={14} />{process.isPending ? "Working…" : "Tidy with AI"}</button>
            <button className="btn-quiet" disabled={!body.trim() || process.isPending} onClick={() => process.mutate(false)}><Wand2 size={14} />Tidy without AI</button>
            <button className="btn-quiet ml-auto" disabled={!body.trim() || save.isPending} onClick={() => save.mutate()}>{selected ? "Save changes" : "Save note"}</button>
            {selected && <button className="btn-danger" onClick={() => { if (confirm("Delete this note?")) del.mutate(selected.id); }}><Trash2 size={14} /></button>}
          </div>
          <ErrorNote error={process.error ?? save.error ?? del.error} />
        </section>
        <section className="flex flex-col gap-3">
          <div className="eyebrow">structured</div>
          {!processed ? <Empty>Tidy the draft to preview it here.</Empty> : (
            <article className="card p-4">
              <div className="mb-2 flex flex-wrap gap-1">{processed.tags.map((t) => <Tag key={t}>{t}</Tag>)}<span className="ml-auto font-mono text-[11px] text-muted">{processed.used_llm ? "AI" : "rules"}</span></div>
              <div className="prose-answer text-[14px]"><ReactMarkdown>{processed.markdown}</ReactMarkdown></div>
            </article>
          )}
          {selected && (
            <div className="card flex flex-col gap-2 p-4">
              <div className="eyebrow">promote to library</div>
              {selected.entry_id ? <div className="text-[13px]">Already in the library: <Link className="underline" to={`/library/${selected.entry_id}`}>open entry</Link></div> : (
                <>
                  <ScopePicker categoryId={cat} topicId={topic} onChange={(c, t) => { setCat(c); setTopic(t); }} />
                  <button className="btn-primary self-start" disabled={promote.isPending} onClick={() => promote.mutate()}>Add to library</button>
                  <ErrorNote error={promote.error} />
                </>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
