import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FileText, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet, apiPost } from "@/lib/api";
import type { ModuleItem } from "@/lib/types";

interface Props { kind: string; title: string; eyebrow: string; description: string }
export default function ModulePage({ kind, title, eyebrow, description }: Props) {
  const client = useQueryClient(); const [newTitle, setNewTitle] = useState("");
  const query = useQuery({ queryKey: ["module", kind], queryFn: () => apiGet<ModuleItem[]>(`/modules/${kind}`) });
  const create = useMutation({ mutationFn: () => apiPost<ModuleItem>(`/modules/${kind}`, { title: newTitle }), onSuccess: () => { setNewTitle(""); void client.invalidateQueries({ queryKey: ["module", kind] }); toast.success(`${title} item created`); } });
  return <div className="space-y-8" data-testid={`${kind}-page`}><section className="flex flex-col justify-between gap-5 border-b border-white/10 pb-7 md:flex-row md:items-end"><div><p className="mb-3 font-mono text-[10px] uppercase tracking-[0.28em] text-[#4d8aff]">{eyebrow}</p><h1 className="text-4xl font-light tracking-[-0.05em]">{title}</h1><p className="mt-3 max-w-xl text-sm leading-6 text-zinc-500">{description}</p></div></section><Card className="border-white/10 bg-[#121212] p-5"><div className="flex gap-2"><Input data-testid={`${kind}-new-input`} value={newTitle} onChange={(event) => setNewTitle(event.target.value)} placeholder={`Add a ${title.toLowerCase()} item`} className="border-white/10 bg-[#0d0e10]" /><Button data-testid={`${kind}-add-button`} disabled={!newTitle.trim() || create.isPending} onClick={() => create.mutate()} className="bg-[#0055ff] text-white hover:bg-[#0044cc]"><Plus className="size-4" />Add</Button></div></Card><div className="grid gap-4 md:grid-cols-2">{(query.data ?? []).map((item) => <Card key={item.id} className="border-white/10 bg-[#121212] p-5" data-testid={`${kind}-item-${item.id}`}><div className="mb-5 grid size-9 place-items-center rounded-md bg-white/5 text-zinc-400"><FileText className="size-4" /></div><p className="text-sm text-zinc-200">{item.title}</p><p className="mt-2 text-xs text-zinc-600">Active signal · {new Date(item.updated_at).toLocaleDateString()}</p></Card>)}{!query.data?.length && <Card className="border-white/10 bg-[#121212] p-12 text-center md:col-span-2"><p className="text-sm text-zinc-500">Nothing here yet. Add the first signal above.</p></Card>}</div></div>;
}