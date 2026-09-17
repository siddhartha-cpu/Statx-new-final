import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowRight, LockKeyhole, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiPost } from "@/lib/api";
import { beginSession } from "@/lib/session";
import type { UserPublic } from "@/lib/types";

export default function Auth() {
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: () => apiPost<UserPublic>(registering ? "/auth/register" : "/auth/login", registering ? { email, password, display_name: displayName } : { email, password }),
    onSuccess: () => { beginSession(); navigate("/app"); },
    onError: (error: Error) => toast.error(error.message || "Unable to sign in"),
  });

  return (
    <main className="grid min-h-svh bg-[#0a0a0a] lg:grid-cols-[1fr_520px]" data-testid="auth-page">
      <section className="relative hidden overflow-hidden border-r border-white/10 p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 opacity-30" style={{ backgroundImage: "linear-gradient(rgba(0,85,255,.16) 1px, transparent 1px), linear-gradient(90deg, rgba(0,85,255,.16) 1px, transparent 1px)", backgroundSize: "64px 64px" }} />
        <div className="relative z-10 flex items-center gap-3" data-testid="auth-brand">
          <div className="grid size-9 place-items-center rounded-md bg-[#0055ff] font-mono text-sm font-bold">SX</div>
          <span className="font-mono text-sm tracking-[0.24em] text-white">STATX AI</span>
        </div>
        <div className="relative z-10 max-w-xl">
          <p className="mb-6 font-mono text-xs uppercase tracking-[0.32em] text-[#4d8aff]">Unified intelligence layer</p>
          <h1 className="max-w-2xl text-5xl font-light leading-[1.02] tracking-[-0.05em] text-white xl:text-7xl">One workspace.<br /><span className="text-white/45">Every useful model.</span></h1>
          <p className="mt-7 max-w-lg text-base leading-7 text-zinc-400">Statx routes each prompt across your connected AI providers, keeps context intact, and brings live sources into the conversation when the answer depends on now.</p>
        </div>
        <div className="relative z-10 flex items-center gap-6 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-500"><span>AI ROUTING</span><span>·</span><span>SAFE FALLBACK</span><span>·</span><span>LIVE RESEARCH</span></div>
      </section>
      <section className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-sm" data-testid="auth-form">
          <div className="mb-10 lg:hidden" data-testid="auth-mobile-brand"><div className="mb-5 grid size-9 place-items-center rounded-md bg-[#0055ff] font-mono text-sm font-bold">SX</div><p className="font-mono text-xs tracking-[0.24em] text-white">STATX AI</p></div>
          <div className="mb-9">
            <div className="mb-4 flex items-center gap-2 text-[#4d8aff]"><Sparkles className="size-4" /><span className="font-mono text-[10px] uppercase tracking-[0.24em]">Private workspace</span></div>
            <h2 className="text-3xl font-light tracking-[-0.04em] text-white">{registering ? "Create your workspace" : "Welcome back"}</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">{registering ? "Start with your Statx identity. Provider credentials stay server-side." : "Continue where your thinking left off."}</p>
          </div>
          <div className="space-y-4">
            {registering && <Input data-testid="auth-display-name-input" value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Display name" autoComplete="name" />}
            <Input data-testid="auth-email-input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@company.com" type="email" autoComplete="email" />
            <Input data-testid="auth-password-input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" autoComplete={registering ? "new-password" : "current-password"} />
            <Button data-testid="auth-submit-button" className="h-11 w-full bg-[#0055ff] text-white hover:bg-[#0044cc]" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Working…" : registering ? "Create workspace" : "Sign in"}<ArrowRight className="size-4" /></Button>
          </div>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-zinc-500"><LockKeyhole className="size-3" /> Sessions are encrypted and httpOnly</div>
          <button data-testid="auth-mode-toggle" className="mt-9 w-full text-center text-sm text-zinc-400 hover:text-white" onClick={() => setRegistering((value) => !value)}>{registering ? "Already have a workspace? Sign in" : "New to Statx? Create a workspace"}</button>
        </div>
      </section>
    </main>
  );
}