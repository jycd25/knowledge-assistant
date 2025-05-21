// Mirrors src/knowledge_assistant/api/schemas.py. Keep the two in sync by hand.
export interface Category { id: string; name: string; description: string; created_at: string; topic_count: number }
export interface Topic { id: string; category_id: string; name: string; description: string; created_at: string; entry_count: number }
export interface EntrySummary { id: string; title: string; topic_id: string | null; source: string; tags: string[]; created_at: string; updated_at: string; preview: string }
export interface Entry extends EntrySummary { content: string; chunk_count: number }
export interface SearchHit { chunk_id: string; entry_id: string; entry_title: string; topic_id: string | null; text: string; score: number; vector_rank: number | null; keyword_rank: number | null }
export type SearchMode = "hybrid" | "vector" | "keyword";
export interface Job { id: string; kind: string; label: string; status: "queued" | "running" | "done" | "failed"; progress: number; message: string; error: string | null; result: Record<string, unknown>; attempts: number; created_at: string; finished_at: string | null }
export interface Note { id: string; title: string; body: string; processed_body: string | null; tags: string[]; entry_id: string | null; created_at: string; updated_at: string }
export interface ProcessedNote { title: string; markdown: string; tags: string[]; used_llm: boolean; applied_preferences: Record<string, unknown>[] }
export interface Template { id: string; name: string; kind: string; body: string; created_at: string }
export interface Preference { key: string; value: string; explanation: string; updated_at: string }
export interface Settings { llm_provider: string; llm_model: string; llm_available: boolean; embedding_model: string; embedding_dim: number; data_dir: string; entry_count: number; chunk_count: number }
