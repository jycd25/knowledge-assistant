import type * as T from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<R>(path: string, init: RequestInit = {}): Promise<R> {
  const res = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* non-json error body */ }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? (undefined as R) : res.json();
}
const json = (body: unknown) => JSON.stringify(body);

export const api = {
  categories: () => request<T.Category[]>("/categories"),
  createCategory: (b: { name: string; description?: string }) => request<T.Category>("/categories", { method: "POST", body: json(b) }),
  updateCategory: (id: string, b: { name?: string; description?: string }) => request<T.Category>(`/categories/${id}`, { method: "PATCH", body: json(b) }),
  deleteCategory: (id: string) => request<void>(`/categories/${id}`, { method: "DELETE" }),

  topics: (categoryId?: string) => request<T.Topic[]>(`/topics${categoryId ? `?category_id=${categoryId}` : ""}`),
  createTopic: (b: { category_id: string; name: string; description?: string }) => request<T.Topic>("/topics", { method: "POST", body: json(b) }),
  updateTopic: (id: string, b: { name?: string; description?: string }) => request<T.Topic>(`/topics/${id}`, { method: "PATCH", body: json(b) }),
  deleteTopic: (id: string) => request<void>(`/topics/${id}`, { method: "DELETE" }),

  entries: (q: { topic_id?: string; category_id?: string } = {}) => {
    const p = new URLSearchParams(Object.entries(q).filter(([, v]) => v) as [string, string][]);
    return request<T.EntrySummary[]>(`/entries?${p}`);
  },
  entry: (id: string) => request<T.Entry>(`/entries/${id}`),
  createEntry: (b: { title: string; content: string; topic_id?: string | null; tags?: string[] }) => request<T.Entry>("/entries", { method: "POST", body: json(b) }),
  updateEntry: (id: string, b: { title?: string; content?: string; topic_id?: string | null; clear_topic?: boolean; tags?: string[] }) => request<T.Entry>(`/entries/${id}`, { method: "PATCH", body: json(b) }),
  deleteEntry: (id: string) => request<void>(`/entries/${id}`, { method: "DELETE" }),

  search: (b: { query: string; limit?: number; category_id?: string | null; topic_id?: string | null; mode?: T.SearchMode; max_distance?: number }) =>
    request<T.SearchHit[]>("/search", { method: "POST", body: json(b) }),
};

/** Parse a fetch() body as server-sent events. Yields {event, data}. */
export async function* sse(res: Response): AsyncGenerator<{ event: string; data: unknown }> {
  if (!res.ok || !res.body) throw new ApiError(res.status, res.statusText);
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message", data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      yield { event, data: data ? JSON.parse(data) : null };
    }
  }
}

export function askStream(b: { question: string; category_id?: string | null; topic_id?: string | null }, signal?: AbortSignal) {
  return fetch(`${BASE}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: json(b), signal }).then(sse);
}
