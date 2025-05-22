import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "../lib/api";
import { ErrorNote, PageHeader } from "../components/ui";

export default function SettingsPage() {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences });
  const [msg, setMsg] = useState("");
  const [log, setLog] = useState<{ who: "you" | "assistant"; text: string; suggested?: Record<string, string>[] }[]>([]);
  const invalidate = () => qc.invalidateQueries({ queryKey: ["preferences"] });
  const chat = useMutation({
    mutationFn: api.preferenceChat,
    onSuccess: (r, m) => { setLog((l) => [...l, { who: "you", text: m }, { who: "assistant", text: r.message, suggested: r.suggested }]); setMsg(""); void invalidate(); },
  });
  const set = useMutation({ mutationFn: api.setPreference, onSuccess: invalidate });
  const del = useMutation({ mutationFn: api.deletePreference, onSuccess: invalidate });
  const s = settings.data;

  return (
    <div>
      <PageHeader title="Settings" />
      <div className="grid grid-cols-2 gap-6">
        <section className="flex flex-col gap-4">
          <div className="card p-4">
            <div className="eyebrow mb-3">this installation</div>
            {s && (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[14px]">
                <dt className="text-muted">Answers by</dt><dd className="font-mono">{s.llm_provider}{s.llm_model && ` · ${s.llm_model}`} {s.llm_available ? "" : <span className="text-stamp">(not reachable)</span>}</dd>
                <dt className="text-muted">Embeddings</dt><dd className="font-mono">{s.embedding_model} · {s.embedding_dim}d · local</dd>
                <dt className="text-muted">Library</dt><dd className="font-mono">{s.entry_count} entries · {s.chunk_count} passages</dd>
                <dt className="text-muted">Data folder</dt><dd className="break-all font-mono text-[12px]">{s.data_dir}</dd>
              </dl>
            )}
            <p className="mt-3 text-[13px] text-muted">
              Providers are set with environment variables before starting: <code className="font-mono">KA_LLM_PROVIDER</code> (ollama, openai, anthropic),{" "}
              <code className="font-mono">KA_LLM_MODEL</code>, and <code className="font-mono">KA_OPENAI_API_KEY</code> / <code className="font-mono">KA_ANTHROPIC_API_KEY</code>. Search and import never need a network.
            </p>
          </div>
          <div className="card p-4">
            <div className="eyebrow mb-3">note preferences</div>
            <p className="mb-3 text-[13px] text-muted">Applied every time a note is tidied with AI.</p>
            {prefs.data?.length === 0 && <div className="text-[13px] text-muted">None yet — add one below or describe it in the chat.</div>}
            <ul className="flex flex-col gap-1">
              {prefs.data?.map((p) => (
                <li key={p.key} className="group flex items-start gap-2 rounded-card px-2 py-1.5 text-[14px] hover:bg-paper">
                  <div className="min-w-0 flex-1"><span className="font-medium">{p.key}</span>: {p.value}{p.explanation && <div className="text-[12px] text-muted">{p.explanation}</div>}</div>
                  <button aria-label="Remove" className="hidden p-0.5 text-muted hover:text-stamp group-hover:block" onClick={() => del.mutate(p.key)}><Trash2 size={12} /></button>
                </li>
              ))}
            </ul>
            <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); set.mutate({ key: String(f.get("k")), value: String(f.get("v")) }); e.currentTarget.reset(); }}>
              <input name="k" className="field" placeholder="Preference (e.g. style)" required />
              <input name="v" className="field" placeholder="Value (e.g. casual, short)" required />
              <button className="btn-quiet">Add</button>
            </form>
          </div>
        </section>
        <section className="card flex flex-col p-4">
          <div className="eyebrow mb-3">describe preferences in plain language</div>
          <div className="flex min-h-64 flex-1 flex-col gap-2 overflow-y-auto">
            {log.length === 0 && <div className="text-[13px] text-muted">Try: “I like bullet points and a short summary at the top.”</div>}
            {log.map((m, i) => (
              <div key={i} className={`max-w-[85%] rounded-card px-3 py-2 text-[14px] ${m.who === "you" ? "self-end bg-ink text-paper" : "bg-paper"}`}>
                {m.text}
                {m.suggested && m.suggested.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {m.suggested.map((sg) => (
                      <button key={sg.key} className="btn-quiet justify-between py-1 text-[13px]" onClick={() => set.mutate({ key: sg.key, value: sg.value, explanation: sg.explanation })}>
                        <span>{sg.key}: {sg.value}</span><span className="text-muted">save</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <ErrorNote error={chat.error} />
          <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (msg.trim()) chat.mutate(msg); }}>
            <input className="field" value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Tell me how you like your notes" />
            <button className="btn-primary" disabled={chat.isPending || !msg.trim()}>{chat.isPending ? "…" : "Send"}</button>
          </form>
        </section>
      </div>
    </div>
  );
}
