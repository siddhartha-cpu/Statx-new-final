import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTheme } from "next-themes";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";
import { Activity, BrainCircuit, ChevronRight, ClipboardCheck, FileText, History as HistoryIcon, LayoutDashboard, LogOut, Moon, Settings2, Sun } from "lucide-react";
import { apiGet } from "@/lib/api";
import { endSession } from "@/lib/session";
import type { UserPublic } from "@/lib/types";

const primaryLinks = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/workspace", label: "AI Workspace", icon: BrainCircuit },
  { to: "/app/documents", label: "Documents", icon: FileText },
];
const insightLinks = [
  { to: "/app/history", label: "History", icon: HistoryIcon },
  { to: "/app/results", label: "Results", icon: Activity },
  { to: "/app/assignments", label: "Assignments", icon: ClipboardCheck },
];
const mobileLinks = [...primaryLinks.map(({ to, label, icon }) => ({ to, label, icon })), ...insightLinks, { to: "/app/settings", label: "Settings", icon: Settings2 }];

export default function Layout() {
  const location = useLocation();
  const { resolvedTheme, setTheme } = useTheme();
  const me = useQuery({ queryKey: ["me"], queryFn: () => apiGet<UserPublic>("/auth/me"), retry: false });
  useEffect(() => { if (me.isError) window.history.replaceState({}, "", "/login"); }, [me.isError]);
  if (me.isError) return <Navigate to="/login" replace />;
  const name = me.data?.display_name ?? "Loading…";
  return (
    <div className="min-h-svh bg-[#0a0a0a] text-white lg:grid lg:grid-cols-[236px_1fr]" data-testid="app-shell">
      <aside className="hidden border-r border-white/10 bg-[#0d0d0e] lg:flex lg:flex-col" data-testid="app-sidebar">
        <div className="flex h-20 items-center gap-3 border-b border-white/10 px-5"><div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 font-mono text-xs font-bold text-white shadow-lg shadow-indigo-200">SN</div><div><p className="font-mono text-xs tracking-[0.17em]">STATNEX AI</p><p className="mt-0.5 text-[10px] text-zinc-600">SMART WORKSPACE</p></div></div>
        <nav className="flex-1 space-y-7 p-3 pt-7">
          <div><p className="mb-2 px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-zinc-600">Workspace</p>{primaryLinks.map(({ to, label, icon: Icon, end }) => <NavLink key={to} end={end} to={to} data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-")}`} className={({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? "bg-gradient-to-r from-indigo-50 to-blue-50 font-medium text-indigo-700" : "text-zinc-500 hover:bg-white/5 hover:text-slate-900"}`}><Icon className="size-4" /><span>{label}</span>{location.pathname === to && <ChevronRight className="ml-auto size-3 text-indigo-500" />}</NavLink>)}</div>
          <div><p className="mb-2 px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-zinc-600">Insights</p>{insightLinks.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} data-testid={`nav-${label.toLowerCase()}`} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${isActive ? "bg-gradient-to-r from-emerald-50 to-cyan-50 font-medium text-emerald-700" : "text-zinc-500 hover:bg-white/5 hover:text-slate-900"}`}><Icon className="size-4" /><span>{label}</span></NavLink>)}</div>
        </nav>
        <div className="border-t border-white/10 p-3"><NavLink to="/app/settings" data-testid="nav-settings" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-zinc-500 hover:bg-white/5 hover:text-slate-900"><Settings2 className="size-4" />Settings</NavLink><button data-testid="logout-button" className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-zinc-500 hover:bg-red-50 hover:text-red-600" onClick={() => void endSession()}><LogOut className="size-4" />Sign out</button></div>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-black/70 px-5 backdrop-blur-xl sm:px-8" data-testid="app-header"><div className="flex items-center gap-3 lg:hidden"><div className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 font-mono text-[10px] font-bold text-white">SN</div><span className="font-mono text-xs tracking-[0.17em]">STATNEX AI</span></div><div className="hidden text-xs capitalize text-zinc-500 lg:block">{location.pathname === "/app" ? "Workspace overview" : location.pathname.split("/").pop()?.replace("-", " ")}</div><div className="flex items-center gap-2"><button data-testid="theme-toggle-button" aria-label={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`} onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} className="grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm hover:border-indigo-300 hover:text-indigo-600">{resolvedTheme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}</button><NavLink to="/app/settings" data-testid="header-profile-button" className="group flex items-center gap-3 rounded-xl px-2 py-1.5 hover:bg-indigo-50"><span className="max-w-36 truncate text-sm font-medium text-slate-700" data-testid="header-user-name">{name}</span><div className="grid size-9 place-items-center overflow-hidden rounded-full bg-gradient-to-br from-indigo-500 to-blue-600 text-xs font-semibold text-white shadow-sm" data-testid="header-user-avatar">{me.data?.avatar_url ? <img src={me.data.avatar_url} alt={name} className="h-full w-full object-cover" /> : name.slice(0, 1).toUpperCase()}</div></NavLink></div></header>
        <nav className="flex gap-1 overflow-x-auto border-b border-white/10 bg-white px-3 py-2 lg:hidden" data-testid="mobile-navigation">{mobileLinks.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} data-testid={`mobile-nav-${label.toLowerCase().replaceAll(" ", "-")}`} className={({ isActive }) => `flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-xs ${isActive ? "bg-indigo-50 font-medium text-indigo-700" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"}`}><Icon className="size-3.5" />{label}</NavLink>)}</nav>
        <div className="pointer-events-none fixed right-10 top-24 -z-0 size-56 rounded-full bg-cyan-100/40 blur-3xl" /><div className="pointer-events-none fixed bottom-8 left-1/3 -z-0 size-64 rounded-full bg-indigo-100/40 blur-3xl" />
        <main className="relative z-10 mx-auto max-w-[1450px] p-5 sm:p-8"><Outlet /></main>
      </div>
    </div>
  );
}