import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DocumentAnalysis } from "@/lib/types";

function clean(text: string) { return text.replaceAll("**", "").trim(); }

function parseFlashcards(content: string) {
  const cards: { question: string; answer: string }[] = [];
  let question = "";
  let answer = "";
  for (const raw of clean(content).split("\n")) {
    const line = raw.trim();
    const q = line.match(/^(?:Q(?:uestion)?\s*\d*)[.:)\-]\s*(.+)$/i);
    const a = line.match(/^(?:A(?:nswer)?\s*\d*)[.:)\-]\s*(.+)$/i);
    if (q) {
      if (question && answer) cards.push({ question, answer });
      question = q[1]; answer = "";
    } else if (a) answer = a[1];
    else if (answer) answer += ` ${line}`;
    else if (question && line) question += ` ${line}`;
  }
  if (question && answer) cards.push({ question, answer });
  return cards.length ? cards : clean(content).split(/\n\s*\n/).filter(Boolean).map((part, index) => ({ question: `Card ${index + 1}`, answer: part }));
}

function FlashcardDeck({ content }: { content: string }) {
  const cards = useMemo(() => parseFlashcards(content), [content]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  useEffect(() => { setIndex(0); setFlipped(false); }, [content]);
  const card = cards[index];
  const move = (next: number) => { setIndex((next + cards.length) % cards.length); setFlipped(false); };
  return <div className="mx-auto max-w-xl" data-testid="flashcard-deck"><div className="mb-4 flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-600">Flashcard {index + 1} of {cards.length}</p><span className="text-xs text-slate-400">Click to flip</span></div><button data-testid="flashcard-flip-button" onClick={() => setFlipped((value) => !value)} className="flashcard-scene block h-64 w-full text-left"><span className={`flashcard-inner ${flipped ? "is-flipped" : ""}`}><span className="flashcard-face bg-gradient-to-br from-emerald-500 to-teal-600 text-white"><span className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-100">Question</span><span className="mt-5 block font-heading text-2xl font-semibold leading-snug">{card.question}</span><span className="absolute bottom-6 right-6 grid size-9 place-items-center rounded-full bg-white/15"><RotateCcw className="size-4" /></span></span><span className="flashcard-face flashcard-back bg-gradient-to-br from-blue-600 to-indigo-600 text-white"><span className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-100">Answer</span><span className="mt-5 block text-lg font-medium leading-8">{card.answer}</span><span className="absolute bottom-6 right-6 grid size-9 place-items-center rounded-full bg-white/15"><RotateCcw className="size-4" /></span></span></span></button><div className="mt-4 flex items-center justify-center gap-3"><Button data-testid="flashcard-previous-button" variant="outline" size="sm" onClick={() => move(index - 1)}><ChevronLeft className="size-4" />Previous</Button><div className="flex gap-1.5">{cards.map((_, dot) => <span key={dot} className={`size-2 rounded-full ${dot === index ? "bg-emerald-500" : "bg-slate-200"}`} />)}</div><Button data-testid="flashcard-next-button" variant="outline" size="sm" onClick={() => move(index + 1)}>Next<ChevronRight className="size-4" /></Button></div></div>;
}

function RichText({ content, action }: { content: string; action: string }) {
  const blocks = clean(content).split("\n").filter((line) => line.trim());
  return <div className="space-y-3" data-testid={`analysis-${action}-content`}>{blocks.map((raw, index) => { const line = raw.trim(); if (/^#{1,4}\s/.test(line)) return <h3 key={index} className="mt-6 font-heading text-xl font-semibold text-indigo-700">{line.replace(/^#{1,4}\s*/, "")}</h3>; if (/^[-•*]\s/.test(line)) return <div key={index} className="flex gap-3 rounded-xl bg-slate-50 p-3 text-sm leading-6 text-slate-700"><span className="mt-2 size-2 shrink-0 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500" /><span>{line.replace(/^[-•*]\s*/, "")}</span></div>; if (/^\d+[.)]\s/.test(line) && action === "mcqs") return <div key={index} className="mt-4 rounded-2xl border border-amber-100 bg-amber-50/70 p-4 font-semibold text-slate-800">{line}</div>; return <p key={index} className="text-sm leading-7 text-slate-700">{line}</p>; })}</div>;
}

interface ParsedMcq { question: string; options: { key: string; text: string }[]; correct: string; why: string }

function parseMcqs(content: string): ParsedMcq[] {
  const questions: ParsedMcq[] = [];
  let current: ParsedMcq | null = null;
  let collectingWhy = false;
  for (const raw of clean(content).split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const question = line.match(/^(?:Question|Q)\s*\d+\s*[:.)-]\s*(.+)$/i);
    const option = line.match(/^([A-D])\s*[).:-]\s*(.+)$/i);
    const correct = line.match(/^(?:Correct(?:\s+answer)?|Answer)\s*[:.-]\s*([A-D])/i);
    const why = line.match(/^(?:Why|Explanation)\s*[:.-]\s*(.+)$/i);
    if (question) {
      if (current) questions.push(current);
      current = { question: question[1], options: [], correct: "", why: "" };
      collectingWhy = false;
    } else if (current && option) {
      current.options.push({ key: option[1].toUpperCase(), text: option[2] });
      collectingWhy = false;
    } else if (current && correct) {
      current.correct = correct[1].toUpperCase();
      collectingWhy = false;
    } else if (current && why) {
      current.why = why[1];
      collectingWhy = true;
    } else if (current && collectingWhy) current.why += ` ${line}`;
  }
  if (current) questions.push(current);
  return questions.filter((question) => question.question && question.options.length >= 2 && question.correct);
}

function McqDeck({ content, onComplete }: { content: string; onComplete?: (correct: number, total: number) => void }) {
  const questions = useMemo(() => parseMcqs(content), [content]);
  const [selected, setSelected] = useState<Record<number, string>>({});
  useEffect(() => setSelected({}), [content]);
  if (!questions.length) return <RichText content={content} action="mcqs" />;
  const answered = Object.keys(selected).length;
  const score = questions.reduce((total, question, index) => total + (selected[index] === question.correct ? 1 : 0), 0);
  return <div className="space-y-5" data-testid="mcq-deck"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-600">Interactive practice</p><span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">{answered}/{questions.length} answered</span></div>{questions.map((question, index) => { const answer = selected[index]; const correct = answer === question.correct; return <div key={`${question.question}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" data-testid={`mcq-question-${index}`}><div className="flex gap-3"><span className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 text-xs font-bold text-white">{index + 1}</span><p className="font-heading text-base font-semibold leading-6 text-slate-800">{question.question}</p></div><div className="mt-4 grid gap-2 sm:grid-cols-2">{question.options.map((option) => { const isChosen = answer === option.key; const isCorrectOption = Boolean(answer) && option.key === question.correct; const classes = isCorrectOption ? "border-emerald-300 bg-emerald-50 text-emerald-800" : isChosen ? "border-red-300 bg-red-50 text-red-700" : "border-slate-200 bg-slate-50 text-slate-600 hover:border-amber-300 hover:bg-amber-50"; return <button key={option.key} data-testid={`mcq-option-${index}-${option.key}`} onClick={() => setSelected((values) => ({ ...values, [index]: option.key }))} className={`flex items-start gap-3 rounded-xl border p-3 text-left text-sm ${classes}`}><span className="font-bold">{option.key}</span><span>{option.text}</span></button>; })}</div>{answer && <div className={`analysis-enter mt-4 rounded-xl border p-4 ${correct ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`} data-testid={`mcq-feedback-${index}`}><p className={`text-sm font-semibold ${correct ? "text-emerald-700" : "text-amber-800"}`}>{correct ? "Correct" : `Not quite — the correct answer is ${question.correct}`}</p><p className="mt-1 text-xs leading-5 text-slate-600"><span className="font-semibold">Why:</span> {question.why || "This option best matches the information in the document."}</p></div>}</div>; })}{answered === questions.length && onComplete && <div className="rounded-2xl bg-gradient-to-r from-amber-400 to-orange-500 p-5 text-white"><p className="font-heading text-xl font-semibold">You scored {score} out of {questions.length}</p><p className="mt-1 text-sm text-amber-50">Save this attempt to your Results history.</p><Button data-testid="mcq-save-result-button" onClick={() => onComplete(score, questions.length)} className="mt-4 bg-white text-amber-700 hover:bg-amber-50">Save result</Button></div>}</div>;
}

export default function DocumentAnalysisView({ analysis, onMcqComplete }: { analysis: DocumentAnalysis; onMcqComplete?: (correct: number, total: number) => void }) {
  if (analysis.action === "flashcards") return <FlashcardDeck content={analysis.content} />;
  if (analysis.action === "mcqs") return <McqDeck content={analysis.content} onComplete={onMcqComplete} />;
  return <div className="analysis-enter"><div className="mb-5 flex items-center gap-3"><div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 text-white"><Sparkles className="size-5" /></div><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-indigo-600">StatNex AI</p><p className="font-heading text-lg font-semibold capitalize text-slate-900">{analysis.action}</p></div></div><RichText content={analysis.content} action={analysis.action} /></div>;
}