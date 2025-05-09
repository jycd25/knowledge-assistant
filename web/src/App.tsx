import { NavLink, Navigate, Route, Routes } from "react-router";
import { BookOpen, FileUp, LibraryBig, NotebookPen, Search, Settings2 } from "lucide-react";
import SearchPage from "./pages/SearchPage";

const NAV = [
  { to: "/search", label: "Search", icon: Search },
  { to: "/library", label: "Library", icon: LibraryBig },
  { to: "/import", label: "Import", icon: FileUp },
  { to: "/notes", label: "Notes", icon: NotebookPen },
  { to: "/templates", label: "Templates", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings2 },
];

export default function App() {
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
      </aside>
      <main className="min-w-0 flex-1 px-8 py-7">
        <div className="mx-auto max-w-5xl">
          <Routes>
            <Route path="/" element={<Navigate to="/search" replace />} />
            <Route path="/search" element={<SearchPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
