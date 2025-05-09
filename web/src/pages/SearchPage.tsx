import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router";
import ReactMarkdown from "react-markdown";
import { CornerDownLeft, Square } from "lucide-react";
import { api, askStream } from "../lib/api";
import type { SearchHit, SearchMode } from "../lib/types";
import { ErrorNote, Empty } from "../components/ui";

type Tab = "ask" | "find";

export default function SearchPage() {
  const [tab, setTab] = useState<Tab>("ask");
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");

  // ask state
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SearchHit[]>([]);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const find = useMutation({ mutationFn: () => api.search({ query: q, mode, limit: 15 }) });

  async function ask() {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    setAnswer(""); setSources([]); setAskError(null); setAsking(true);
    try {
      for await (const ev of await askStream({ question: q }, ctl.signal)) {
        if (ev.event === "sources") setSources(ev.data as SearchHit[]);
        else if (ev.event === "token") setAnswer((a) => a + (ev.data as string));
        else if (ev.event === "error") setAskError((ev.data as { message: string }).message);
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setAskError(e instanceof Error ? e.message : String(e));
    } finally { setAsking(false); }
  }
  useEffect(() => () => abort.current?.abort(), []);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    if (tab === "ask") void ask(); else find.mutate();
  }

  return (
    <div>
      <form onSubmit={submit} className="card p-4">
        <div className="mb-3 flex items-center gap-1">
          {(["ask", "find"] as Tab[]).map((t) => (
            <button key={t} type="button" onClick={() => setTab(t)}
              className={`rounded-card px-3 py-1.5 text-sm font-medium ${tab === t ? "bg-ink text-paper" : "text-muted hover:text-ink"}`}>
              {t === "ask" ? "Ask a question" : "Find passages"}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <textarea autoFocus rows={2} value={q} onChange={(e) => setQ(e.target.value)}
            placeholder={tab === "ask" ? "What does my library say about…" : "Words or phrases to look for"}
            className="field display resize-none text-[18px] font-medium" />
          {asking
            ? <button type="button" onClick={() => abort.current?.abort()} className="btn-quiet self-end"><Square size={14} />Stop</button>
            : <button type="submit" className="btn-primary self-end" disabled={!q.trim()}><CornerDownLeft size={14} />{tab === "ask" ? "Ask" : "Find"}</button>}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {tab === "find" && (
            <select className="field w-auto" value={mode} onChange={(e) => setMode(e.target.value as SearchMode)}>
              <option value="hybrid">Meaning + keywords</option>
              <option value="vector">Meaning only</option>
              <option value="keyword">Keywords only</option>
            </select>
          )}
        </div>
      </form>

      {tab === "ask" ? (
        <section className="mt-6 grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-6">
          <div>
            <ErrorNote error={askError} />
            {!answer && !asking && !askError && <Empty>Ask something and the answer cites the passages it came from.</Empty>}
            {(answer || asking) && (
              <article className="card p-5">
                <div className="eyebrow mb-3">answer{asking ? " · writing…" : ""}</div>
                <div className="prose-answer text-[15px]"><ReactMarkdown>{answer}</ReactMarkdown></div>
              </article>
            )}
          </div>
          <aside>
            {sources.length > 0 && <div className="eyebrow mb-2">sources</div>}
            <ol className="flex flex-col gap-2">
              {sources.map((s, i) => (
                <li key={s.chunk_id} className="card p-3">
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="cite">[{i + 1}]</span>
                    <Link to={`/library/${s.entry_id}`} className="truncate text-[14px] font-medium hover:underline">{s.entry_title}</Link>
                  </div>
                  <p className="line-clamp-4 text-[13px] leading-snug text-ink-soft">{s.text}</p>
                </li>
              ))}
            </ol>
          </aside>
        </section>
      ) : (
        <section className="mt-6">
          <ErrorNote error={find.error} />
          {find.data?.length === 0 && <Empty>No passages matched. Try fewer words, or switch to “Meaning only”.</Empty>}
          <ol className="flex flex-col gap-2">
            {find.data?.map((h) => (
              <li key={h.chunk_id} className="card p-4">
                <div className="mb-1 flex items-center justify-between gap-3">
                  <Link to={`/library/${h.entry_id}`} className="font-medium hover:underline">{h.entry_title}</Link>
                  <span className="font-mono text-[11px] text-muted">
                    {h.vector_rank && `meaning #${h.vector_rank}`}{h.vector_rank && h.keyword_rank && " · "}{h.keyword_rank && `keyword #${h.keyword_rank}`}
                  </span>
                </div>
                <p className="text-[14px] leading-relaxed text-ink-soft">{h.text}</p>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
