import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { ErrorNote, PageHeader } from "../components/ui";

export default function TemplatesPage() {
  const qc = useQueryClient();
  const builtin = useQuery({ queryKey: ["templates", "builtin"], queryFn: api.builtinTemplates });
  const mine = useQuery({ queryKey: ["templates"], queryFn: api.templates });
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const save = useMutation({ mutationFn: () => api.saveTemplate({ name, body }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["templates"] }); } });
  const del = useMutation({ mutationFn: api.deleteTemplate, onSuccess: () => { void qc.invalidateQueries({ queryKey: ["templates"] }); } });

  return (
    <div>
      <PageHeader title="Templates" lede="Starting structures for notes. Built-in ones can be copied into your own and edited." />
      <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-6">
        <aside className="flex flex-col gap-4">
          <section>
            <div className="eyebrow mb-1.5">built in</div>
            {builtin.data && Object.entries(builtin.data).map(([k, v]) => (
              <button key={k} onClick={() => { setName(`${k} (copy)`); setBody(v); }} className="block w-full rounded-card px-2 py-1.5 text-left text-[14px] capitalize hover:bg-card">{k}</button>
            ))}
          </section>
          <section>
            <div className="eyebrow mb-1.5">yours</div>
            {mine.data?.length === 0 && <div className="px-2 text-[13px] text-muted">None saved yet.</div>}
            {mine.data?.map((t) => (
              <div key={t.id} className="group flex items-center rounded-card px-2 py-1.5 text-[14px] hover:bg-card">
                <button onClick={() => { setName(t.name); setBody(t.body); }} className="min-w-0 flex-1 truncate text-left">{t.name}</button>
                <button aria-label="Delete" className="hidden p-0.5 text-muted hover:text-stamp group-hover:block" onClick={() => { if (confirm(`Delete “${t.name}”?`)) del.mutate(t.id); }}><Trash2 size={12} /></button>
              </div>
            ))}
          </section>
        </aside>
        <form className="card flex flex-col gap-3 p-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
          <input className="field font-medium" placeholder="Template name" value={name} onChange={(e) => setName(e.target.value)} required />
          <textarea className="field min-h-96 font-mono text-[13px]" placeholder="# [Title]&#10;&#10;## Section" value={body} onChange={(e) => setBody(e.target.value)} required />
          <ErrorNote error={save.error} />
          <div className="flex items-center justify-between text-[13px] text-muted">
            <span>{save.isSuccess && !save.isPending ? "Saved." : "Saving with an existing name replaces it."}</span>
            <button className="btn-primary" disabled={save.isPending}>Save template</button>
          </div>
        </form>
      </div>
    </div>
  );
}
