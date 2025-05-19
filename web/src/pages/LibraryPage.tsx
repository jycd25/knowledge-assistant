import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { ChevronRight, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../lib/api";
import type { Category, Topic } from "../lib/types";
import { Empty, ErrorNote, PageHeader, ScopePicker, Tag } from "../components/ui";

export default function LibraryPage() {
  const [cat, setCat] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  return (
    <div>
      <PageHeader title="Library" lede="Categories hold topics; topics hold entries. Deleting a level deletes what's inside it." />
      <div className="grid grid-cols-[240px_minmax(0,1fr)] gap-6">
        <Tree cat={cat} topic={topic} onSelect={(c, t) => { setCat(c); setTopic(t); }} />
        <EntryList cat={cat} topic={topic} />
      </div>
    </div>
  );
}

function Tree({ cat, topic, onSelect }: { cat: string | null; topic: string | null; onSelect: (c: string | null, t: string | null) => void }) {
  const qc = useQueryClient();
  const cats = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const topics = useQuery({ queryKey: ["topics", cat], queryFn: () => api.topics(cat!), enabled: !!cat });
  const invalidate = () => { void qc.invalidateQueries({ queryKey: ["categories"] }); void qc.invalidateQueries({ queryKey: ["topics"] }); void qc.invalidateQueries({ queryKey: ["entries"] }); };
  const addCat = useMutation({ mutationFn: (name: string) => api.createCategory({ name }), onSuccess: invalidate });
  const addTopic = useMutation({ mutationFn: (name: string) => api.createTopic({ category_id: cat!, name }), onSuccess: invalidate });
  const delCat = useMutation({ mutationFn: api.deleteCategory, onSuccess: () => { onSelect(null, null); invalidate(); } });
  const delTopic = useMutation({ mutationFn: api.deleteTopic, onSuccess: () => { onSelect(cat, null); invalidate(); } });
  const renCat = useMutation({ mutationFn: (v: { id: string; name: string }) => api.updateCategory(v.id, { name: v.name }), onSuccess: invalidate });
  const renTopic = useMutation({ mutationFn: (v: { id: string; name: string }) => api.updateTopic(v.id, { name: v.name }), onSuccess: invalidate });

  return (
    <aside className="flex flex-col gap-4">
      <section>
        <div className="eyebrow mb-1.5">categories</div>
        <button onClick={() => onSelect(null, null)} className={`block w-full rounded-card px-2 py-1.5 text-left text-[14px] ${!cat ? "bg-accent-wash text-accent-ink" : "hover:bg-card"}`}>All entries</button>
        {cats.data?.map((c) => (
          <Row<Category> key={c.id} item={c} selected={cat === c.id} count={c.topic_count} countLabel="topics"
            onSelect={() => onSelect(c.id, null)} onRename={(name) => renCat.mutate({ id: c.id, name })}
            onDelete={() => { if (confirm(`Delete “${c.name}” and everything in it?`)) delCat.mutate(c.id); }} />
        ))}
        <InlineAdd placeholder="New category" onAdd={(n) => addCat.mutate(n)} />
        <ErrorNote error={addCat.error} />
      </section>
      {cat && (
        <section>
          <div className="eyebrow mb-1.5">topics</div>
          {topics.data?.length === 0 && <div className="px-2 text-[13px] text-muted">No topics yet.</div>}
          {topics.data?.map((t) => (
            <Row<Topic> key={t.id} item={t} selected={topic === t.id} count={t.entry_count} countLabel="entries"
              onSelect={() => onSelect(cat, t.id)} onRename={(name) => renTopic.mutate({ id: t.id, name })}
              onDelete={() => { if (confirm(`Delete “${t.name}” and its entries?`)) delTopic.mutate(t.id); }} />
          ))}
          <InlineAdd placeholder="New topic" onAdd={(n) => addTopic.mutate(n)} />
          <ErrorNote error={addTopic.error} />
        </section>
      )}
    </aside>
  );
}

function Row<T extends { id: string; name: string }>({ item, selected, count, countLabel, onSelect, onRename, onDelete }:
  { item: T; selected: boolean; count: number; countLabel: string; onSelect: () => void; onRename: (n: string) => void; onDelete: () => void }) {
  return (
    <div className={`group flex items-center gap-1 rounded-card px-2 py-1.5 text-[14px] ${selected ? "bg-accent-wash text-accent-ink" : "hover:bg-card"}`}>
      <button onClick={onSelect} className="min-w-0 flex-1 truncate text-left" title={`${count} ${countLabel}`}>{item.name}</button>
      <span className="font-mono text-[11px] text-muted">{count}</span>
      <button aria-label="Rename" className="hidden rounded p-0.5 text-muted hover:text-ink group-hover:block"
        onClick={() => { const n = prompt("Rename to", item.name); if (n && n !== item.name) onRename(n); }}><Pencil size={12} /></button>
      <button aria-label="Delete" className="hidden rounded p-0.5 text-muted hover:text-stamp group-hover:block" onClick={onDelete}><Trash2 size={12} /></button>
    </div>
  );
}

function InlineAdd({ placeholder, onAdd }: { placeholder: string; onAdd: (name: string) => void }) {
  const [v, setV] = useState("");
  return (
    <form className="mt-1 flex gap-1" onSubmit={(e: FormEvent) => { e.preventDefault(); if (v.trim()) { onAdd(v.trim()); setV(""); } }}>
      <input className="field py-1 text-[13px]" placeholder={placeholder} value={v} onChange={(e) => setV(e.target.value)} />
      <button className="btn-quiet px-2 py-1" aria-label="Add" disabled={!v.trim()}><Plus size={14} /></button>
    </form>
  );
}

function EntryList({ cat, topic }: { cat: string | null; topic: string | null }) {
  const entries = useQuery({ queryKey: ["entries", cat, topic], queryFn: () => api.entries({ category_id: cat ?? undefined, topic_id: topic ?? undefined }) });
  const [adding, setAdding] = useState(false);
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <div className="eyebrow">{entries.data?.length ?? 0} entries</div>
        <button className="btn-quiet" onClick={() => setAdding(true)}><Plus size={14} />Write an entry</button>
      </div>
      {adding && <EntryForm topicId={topic} onDone={() => setAdding(false)} />}
      {entries.data?.length === 0 && !adding && <Empty>Nothing here yet. Import a PDF, promote a note, or write an entry.</Empty>}
      <ul className="flex flex-col gap-2">
        {entries.data?.map((e) => (
          <li key={e.id}>
            <Link to={`/library/${e.id}`} className="card flex items-start justify-between gap-4 p-4 transition-colors hover:border-line-strong">
              <div className="min-w-0">
                <div className="font-medium">{e.title}</div>
                <p className="mt-1 line-clamp-2 text-[13px] text-muted">{e.preview}</p>
                <div className="mt-2 flex flex-wrap gap-1"><Tag>{e.source}</Tag>{e.tags.map((t) => <Tag key={t}>{t}</Tag>)}</div>
              </div>
              <ChevronRight size={16} className="shrink-0 text-muted" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EntryForm({ topicId, onDone, initial }: { topicId: string | null; onDone: () => void; initial?: { id: string; title: string; content: string; tags: string[]; topic_id: string | null } }) {
  const qc = useQueryClient();
  const [title, setTitle] = useState(initial?.title ?? "");
  const [content, setContent] = useState(initial?.content ?? "");
  const [tags, setTags] = useState(initial?.tags.join(", ") ?? "");
  const [cat, setCat] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(initial?.topic_id ?? topicId);
  const save = useMutation({
    mutationFn: () => {
      const tagList = tags.split(",").map((t) => t.trim()).filter(Boolean);
      return initial
        ? api.updateEntry(initial.id, { title, content, tags: tagList, topic_id: topic, clear_topic: !topic })
        : api.createEntry({ title, content, tags: tagList, topic_id: topic });
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["entries"] }); void qc.invalidateQueries({ queryKey: ["entry", initial?.id] }); onDone(); },
  });
  return (
    <form className="card mb-4 flex flex-col gap-3 p-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <input className="field font-medium" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
      <textarea className="field min-h-48 font-mono text-[13px]" placeholder="Content (markdown is fine)" value={content} onChange={(e) => setContent(e.target.value)} required />
      <input className="field" placeholder="Tags, comma separated" value={tags} onChange={(e) => setTags(e.target.value)} />
      <ScopePicker categoryId={cat} topicId={topic} onChange={(c, t) => { setCat(c); setTopic(t); }} />
      <ErrorNote error={save.error} />
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-quiet" onClick={onDone}>Cancel</button>
        <button className="btn-primary" disabled={save.isPending}>{save.isPending ? "Indexing…" : initial ? "Save changes" : "Add to library"}</button>
      </div>
    </form>
  );
}
