// Mirrors src/knowledge_assistant/api/schemas.py. Keep the two in sync by hand.
export interface Category { id: string; name: string; description: string; created_at: string; topic_count: number }
export interface Topic { id: string; category_id: string; name: string; description: string; created_at: string; entry_count: number }
export interface EntrySummary { id: string; title: string; topic_id: string | null; source: string; tags: string[]; created_at: string; updated_at: string; preview: string }
export interface Entry extends EntrySummary { content: string; chunk_count: number }
export interface SearchHit { chunk_id: string; entry_id: string; entry_title: string; topic_id: string | null; text: string; score: number; vector_rank: number | null; keyword_rank: number | null }
export type SearchMode = "hybrid" | "vector" | "keyword";
