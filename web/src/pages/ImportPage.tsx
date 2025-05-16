import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { FileUp } from "lucide-react";
import { api } from "../lib/api";
import type { Job } from "../lib/types";
import { Empty, ErrorNote, PageHeader, ScopePicker, fmtDate } from "../components/ui";

export default function ImportPage() {
  const qc = useQueryClient();
  const [cat, setCat] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const [tags, setTags] = useState("");
  const [drag, setDrag] = useState(false);
  const [text, setText] = useState({ title: "", content: "" });
  const fileInput = useRef<HTMLInputElement>(null);
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs, refetchInterval: (q) => q.state.data?.some((j) => j.status === "queued" || j.status === "running") ? 1500 : false });
  const activeCount = jobs.data?.filter((j) => j.status === "queued" || j.status === "running").length ?? 0;
  const prevActive = useRef(activeCount);
  if (prevActive.current > 0 && activeCount < prevActive.current) void qc.invalidateQueries({ queryKey: ["entries"] });
  prevActive.current = activeCount;
  const refresh = () => { void qc.invalidateQueries({ queryKey: ["jobs"] }); void qc.invalidateQueries({ queryKey: ["entries"] }); };

  const upload = useMutation({
    mutationFn: async (files: File[]) => { for (const f of files) await api.ingestPdf(f, { topic_id: topic, tags }); },
    onSuccess: refresh,
  });
  const paste = useMutation({
    mutationFn: () => api.ingestText({ title: text.title, content: text.content, topic_id: topic, tags: tags.split(",").map((t) => t.trim()).filter(Boolean) }),
    onSuccess: () => { setText({ title: "", content: "" }); refresh(); },
  });

  return (
    <div>
      <PageHeader title="Import" lede="PDFs and pasted text are split into passages and indexed in the background." />
      <div className="grid grid-cols-2 gap-6">
        <section className="flex flex-col gap-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); upload.mutate([...e.dataTransfer.files].filter((f) => f.name.toLowerCase().endsWith(".pdf"))); }}
            onClick={() => fileInput.current?.click()} role="button" tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInput.current?.click(); }}
            className={`card flex cursor-pointer flex-col items-center justify-center gap-2 border-dashed px-6 py-12 text-center transition-colors ${drag ? "border-accent bg-accent-wash" : "hover:border-line-strong"}`}>
            <FileUp size={22} className="text-accent" />
            <div className="font-medium">Drop PDFs here, or click to choose</div>
            <div className="text-[13px] text-muted">Text is extracted locally. Scanned images without a text layer won't import.</div>
            <input ref={fileInput} type="file" accept="application/pdf" multiple hidden onChange={(e) => e.target.files && upload.mutate([...e.target.files])} />
          </div>
          <ErrorNote error={upload.error} />
          <form className="card flex flex-col gap-2 p-4" onSubmit={(e) => { e.preventDefault(); paste.mutate(); }}>
            <div className="eyebrow">or paste text</div>
            <input className="field" placeholder="Title" value={text.title} onChange={(e) => setText({ ...text, title: e.target.value })} required />
            <textarea className="field min-h-32 font-mono text-[13px]" placeholder="Paste anything: an article, meeting minutes, a chapter…" value={text.content} onChange={(e) => setText({ ...text, content: e.target.value })} required />
            <button className="btn-primary self-end" disabled={paste.isPending}>Import text</button>
            <ErrorNote error={paste.error} />
          </form>
          <div className="card flex flex-col gap-2 p-4">
            <div className="eyebrow">file under</div>
            <ScopePicker categoryId={cat} topicId={topic} onChange={(c, t) => { setCat(c); setTopic(t); }} />
            <input className="field" placeholder="Tags for these imports, comma separated" value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>
        </section>
        <section>
          <div className="eyebrow mb-2">recent imports</div>
          {jobs.data?.length === 0 && <Empty>Nothing imported yet.</Empty>}
          <ul className="flex flex-col gap-2">{jobs.data?.map((j) => <JobRow key={j.id} job={j} />)}</ul>
        </section>
      </div>
    </div>
  );
}

function JobRow({ job }: { job: Job }) {
  const p = job.result as { entry_id?: string; chunks?: number };
  const active = job.status === "queued" || job.status === "running";
  return (
    <li className="card p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 truncate text-[14px] font-medium">
          {p.entry_id ? <Link to={`/library/${p.entry_id}`} className="hover:underline">{job.label}</Link> : job.label}
        </div>
        <span className={`font-mono text-[11px] ${job.status === "failed" ? "text-stamp" : job.status === "done" ? "text-accent" : "text-muted"}`}>{job.status}</span>
      </div>
      {active && (
        <div className="mt-2">
          <div className="h-1 overflow-hidden rounded bg-paper"><div className="h-full bg-accent transition-[width]" style={{ width: `${Math.max(3, job.progress)}%` }} /></div>
          <div className="mt-1 text-[12px] text-muted">{job.message || "waiting for a worker"}</div>
        </div>
      )}
      {job.status === "done" && (
        <div className="mt-1 text-[12px] text-muted">
          {p.chunks ?? 0} passages indexed · {fmtDate(job.finished_at ?? job.created_at)}
        </div>
      )}
      {job.status === "failed" && <div className="mt-1 whitespace-pre-wrap text-[12px] text-stamp">{job.error?.split("\n")[0]}</div>}
    </li>
  );
}
