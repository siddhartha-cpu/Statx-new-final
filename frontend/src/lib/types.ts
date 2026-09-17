export interface UserPublic {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
  setup_complete: boolean;
}

export interface ProviderStatus {
  id: string;
  name: string;
  method: string;
  status: string;
  configured: boolean;
  selected: boolean;
  fallback_enabled: boolean;
  priority: number;
  cooldown_until: string | null;
  detail: string;
}

export interface ProviderPreferences {
  provider_ids: string[];
  fallback_enabled: boolean;
}

export interface Citation {
  title: string;
  url: string;
  domain: string;
  snippet: string;
  published_at: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  provider_id: string | null;
  citations: Citation[];
  fallback_notice: string | null;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
  provider_id: string | null;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[];
}

export interface ChatResponse {
  message: Message;
  search_used: boolean;
  search_status: string;
  provider_attempts: string[];
}

export interface ModuleItem {
  id: string;
  kind: string;
  title: string;
  description: string;
  status: string;
  updated_at: string;
  file_name?: string | null;
  file_type?: string | null;
  file_size?: number | null;
}

export interface DocumentAnalysis {
  id: string;
  document_id: string;
  action: "summary" | "notes" | "flashcards" | "mcqs" | "descriptive" | "assignment" | "ask";
  content: string;
  created_at: string;
  prompt?: string | null;
  marks?: number | null;
}

export interface ExamResult {
  id: string;
  document_id: string;
  document_title: string;
  analysis_id: string;
  kind: string;
  correct: number;
  total: number;
  percentage: number;
  submitted_at: string;
}