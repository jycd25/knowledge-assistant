import { NavLink, Navigate, Route, Routes } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, FileUp, LibraryBig, NotebookPen, Search, Settings2 } from "lucide-react";
import { api } from "./lib/api";
import SearchPage from "./pages/SearchPage";
import LibraryPage from "./pages/LibraryPage";
import ImportPage from "./pages/ImportPage";
import NotesPage from "./pages/NotesPage";
import TemplatesPage from "./pages/TemplatesPage";
import SettingsPage from "./pages/SettingsPage";

const NAV = [
  { to: "/search", label: "Search", icon: Search },
  { to: "/library", label: "Library", icon: LibraryBig },
  { to: "/import", label: "Import", icon: FileUp },
  { to: "/notes", label: "Notes", icon: NotebookPen },
  { to: "/templates", label: "Templates", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings2 },
];

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-52 shrink-0 flex-col border-r border-line bg-card px-3 py-5">
        <div className="mb-6 px-2">
          <div className="display text-[17px] font-semibold leading-tight">Knowledge<br />Assistant</div>
          <div className="eyebrow mt-1">local archive</div>
        </div>
        <nav className="flex flex-col gap-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-card px-2.5 py-2 text-[14px] transition-colors ${isActive ? "bg-accent-wash font-medium text-accent-ink" : "text-ink-soft hover:bg-paper hover:text-ink"}`}>
              <Icon size={16} strokeWidth={1.75} />{label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-2 text-[12px] text-muted">
          {health.isError ? <span className="text-stamp">Server not reachable</span>
            : health.data ? <>LLM: <span className="font-mono">{health.data.llm_provider}</span>{health.data.llm_available ? "" : " (offline)"}</>
            : "connecting…"}
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-8 py-7">
        <div className="mx-auto max-w-5xl">
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/library/:entryId" element={<LibraryPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/notes" element={<NotesPage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
