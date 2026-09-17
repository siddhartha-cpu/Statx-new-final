import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { Activity, BookOpen, BrainCircuit, ChevronRight, ClipboardCheck, FileText, Gauge, LayoutDashboard, LogOut, MessageSquare, Network, Settings2 } from "lucide-react";
import { apiGet } from "@/lib/api";
import { endSession } from "@/lib/session";
import type { UserPublic } from "@/lib/types";

const links = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/workspace", label: "AI Workspace", icon: BrainCircuit },
  { to: "/app/conversations", label: "Conversations", icon: MessageSquare },
  { to: "/app/providers", label: "Providers", icon: Network },
];
const moduleLinks = [
  { to: "/app/documents", label: "Documents", icon: FileText },
  { to: "/app/competency", label: "Competency", icon: Gauge },
  { to: "/app/results", label: "Results", icon: Activity },
  { to: "/app/assessment", label: "Assessment", icon: ClipboardCheck },
];

export default function Layout() {
  const location = useLocation();
  const me = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), retry: false });
  useEffect(() => { if (me.isError) window.history.replaceState({}, "", "/login"); }, [me.isError]);
  if (me.isError) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-svh bg-[#0a0a0a] text-white lg:grid lg:grid-cols-[248px_1fr]" data-testid="app-shell">
      <aside className="hidden border-r border-white/10 bg-[#0d0d0e] lg:flex lg:flex-col" data-testid="app-sidebar">
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-6"><div className="grid size-8 place-items-center rounded-md bg-[#0055ff] font-mono text-xs font-bold">SX</div><div><p className="font-mono text-xs tracking-[0.2em]">STATX AI</p><p className="mt-0.5 text-[10px] text-zinc-600">INTELLIGENCE OS</p></div></div>
        <nav className="flex-1 space-y-7 p-4 pt-8">
          <div><p className="mb-3 px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-zinc-600">Core</p>{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} end={end} to={to} data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-")}`} className={({ isActive }) => `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm ${isActive ? "bg-[#0055ff]/15 text-white" : "text-zinc-500 hover:bg-white/5 hover:text-white"}`}><Icon className="size-4" /><span>{label}</span>{location.pathname === to && <ChevronRight className="ml-auto size-3 text-[#4d8aff]" />}</NavLink>)}</div>
          <div><p className="mb-3 px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-zinc-600">Signal library</p>{moduleLinks.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} data-testid={`nav-${label.toLowerCase()}`} className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm ${isActive ? "bg-white/8 text-white" : "text-zinc-500 hover:bg-white/5 hover:text-white"}`}><Icon className="size-4" /><span>{label}</span></NavLink>)}</div>
        </nav>
        <div className="border-t border-white/10 p-4"><NavLink to="/app/settings" data-testid="nav-settings" className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-zinc-500 hover:bg-white/5 hover:text-white"><Settings2 className="size-4" />Settings</NavLink><button data-testid="logout-button" className="mt-2 flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm text-zinc-600 hover:bg-red-500/10 hover:text-red-300" onClick={() => void endSession()}><LogOut className="size-4" />Sign out</button></div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-black/70 px-5 backdrop-blur-xl sm:px-8" data-testid="app-header"><div className="flex items-center gap-3 lg:hidden"><div className="grid size-7 place-items-center rounded bg-[#0055ff] font-mono text-[10px] font-bold">SX</div><span className="font-mono text-xs tracking-[0.2em]">STATX AI</span></div><div className="hidden text-xs text-zinc-500 lg:block">{location.pathname === "/app" ? "Workspace overview" : location.pathname.split("/").pop()?.replace("-", " ")}</div><div className="flex items-center gap-3"><span className="hidden font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-600 sm:block" data-testid="header-user-email">{me.data?.email ?? "Loading identity"}</span><div className="grid size-8 place-items-center rounded-full border border-[#0055ff]/40 bg-[#0055ff]/10 text-xs text-[#6d9fff]" data-testid="header-user-avatar">{me.data?.display_name?.slice(0, 1).toUpperCase() ?? "S"}</div></div></header>
        <main className="mx-auto max-w-[1500px] p-5 sm:p-8"><Outlet /></main>
      </div>
    </div>
  );
}