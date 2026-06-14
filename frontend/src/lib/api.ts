const API_BASE = import.meta.env.PUBLIC_API_URL ?? '';

export type MeetingType = 'general' | 'standup' | 'planning' | 'review';

export const MEETING_TYPE_LABELS: Record<MeetingType, string> = {
  general: 'عمومی',
  standup: 'استنداپ',
  planning: 'برنامه‌ریزی',
  review: 'مرور',
};

export interface MeetingTask {
  title: string;
  title_en?: string;
  assignee?: string | null;
  deadline?: string | null;
  priority: 'high' | 'medium' | 'low';
  context: string;
  context_en?: string;
  detail?: string;
  detail_en?: string;
  acceptance_criteria?: string[];
  acceptance_criteria_en?: string[];
  jira_key?: string | null;
}

export interface MeetingAnalysis {
  title: string;
  title_en?: string;
  summary: string;
  key_points: string[];
  decisions: string[];
  tasks: MeetingTask[];
}

export interface MeetingRecord {
  id: string;
  title: string;
  transcript: string;
  analysis: MeetingAnalysis;
  created_at: string;
  source: string;
  meeting_type?: MeetingType;
  tags?: string[];
  project_key?: string;
}

export interface ActionItem {
  meeting_id: string;
  meeting_title: string;
  meeting_type: MeetingType;
  project_key: string;
  task_index: number;
  title: string;
  title_en?: string;
  assignee?: string | null;
  deadline?: string | null;
  priority: 'high' | 'medium' | 'low';
  jira_key?: string | null;
}

export interface SpeakerStat {
  speaker: string;
  turns: number;
  percent: number;
}

export interface SpeakerJiraMap {
  speaker_name: string;
  jira_account_id: string;
  jira_display_name: string;
}

export interface RagAnswer {
  answer: string;
  sources: { speaker: string; chunk_id: string; excerpt?: string; text?: string }[];
  used_meeting_context?: boolean;
}

export interface JiraPreviewIssue {
  summary: string;
  description: string;
  priority: string;
  task_index: number;
}

export interface TranscribeResponse {
  transcript: string;
}

export interface FacilitationReport {
  what_went_well: string[];
  improvements: string[];
  next_meeting_agenda: string[];
  timebox_suggestion: string;
  coaching_summary: string;
  facilitator_score: number | null;
}

export interface HealthResponse {
  status: string;
  google_api: boolean;
  jira_configured: boolean;
  jira_site?: string;
  database?: string;
}

export interface ListMeetingsParams {
  q?: string;
  type?: MeetingType;
  project?: string;
  tag?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? 'خطای سرور');
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function buildQuery(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v?.trim()) q.set(k, v.trim());
  }
  const s = q.toString();
  return s ? `?${s}` : '';
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  listMeetings: (params: ListMeetingsParams = {}) =>
    request<MeetingRecord[]>(
      `/api/meetings${buildQuery({
        q: params.q,
        type: params.type,
        project: params.project,
        tag: params.tag,
      })}`
    ),
  listTasks: (openOnly = false) =>
    request<ActionItem[]>(`/api/tasks${openOnly ? '?open_only=true' : ''}`),
  listSynthetic: () => request<{ id: string; filename: string; title: string }[]>('/api/meetings/synthetic'),
  createFromSynthetic: (id: string) =>
    request<MeetingRecord>(`/api/meetings/synthetic/${id}`, { method: 'POST' }),
  createMeeting: (
    transcript: string,
    opts?: { title?: string; meetingType?: MeetingType; tags?: string[]; projectKey?: string }
  ) =>
    request<MeetingRecord>('/api/meetings', {
      method: 'POST',
      body: JSON.stringify({
        transcript,
        title: opts?.title,
        meeting_type: opts?.meetingType ?? 'general',
        tags: opts?.tags ?? [],
        project_key: opts?.projectKey ?? '',
      }),
    }),
  transcribeAudio: async (file: Blob, filename = 'recording.webm') => {
    const form = new FormData();
    form.append('file', file, filename);
    const res = await fetch(`${API_BASE}/api/transcribe`, { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail ?? 'خطای رونویسی');
    }
    return res.json() as Promise<TranscribeResponse>;
  },
  getMeeting: (id: string) => request<MeetingRecord>(`/api/meetings/${id}`),
  updateMeeting: (id: string, body: Partial<{ title: string; tags: string[]; project_key: string; meeting_type: MeetingType }>) =>
    request<MeetingRecord>(`/api/meetings/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteMeeting: (id: string) =>
    request<{ deleted: string }>(`/api/meetings/${id}`, { method: 'DELETE' }),
  getSpeakers: (id: string) => request<SpeakerStat[]>(`/api/meetings/${id}/speakers`),
  getFacilitation: (id: string) =>
    request<FacilitationReport>(`/api/meetings/${id}/facilitation`),
  exportUrl: (id: string) => `${API_BASE}/api/meetings/${id}/export`,
  ask: (id: string, question: string) =>
    request<RagAnswer>(`/api/meetings/${id}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
  jiraPreview: (id: string) =>
    request<{ issues: JiraPreviewIssue[] }>(`/api/meetings/${id}/jira/preview`, { method: 'POST' }),
  jiraCreate: (id: string, task_indices?: number[]) =>
    request<{ created: { key: string; summary: string; task_index?: number }[] }>(
      `/api/meetings/${id}/jira/create`,
      { method: 'POST', body: JSON.stringify({ task_indices }) }
    ),
  listAssigneeMap: () => request<SpeakerJiraMap[]>('/api/settings/assignee-map'),
  upsertAssigneeMap: (entry: SpeakerJiraMap) =>
    request<SpeakerJiraMap>('/api/settings/assignee-map', {
      method: 'PUT',
      body: JSON.stringify(entry),
    }),
  deleteAssigneeMap: (speaker: string) =>
    request<{ deleted: string }>(`/api/settings/assignee-map/${encodeURIComponent(speaker)}`, {
      method: 'DELETE',
    }),
};

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export function priorityBadgeClass(p: string): string {
  if (p === 'high') return 'badge badge-high';
  if (p === 'low') return 'badge badge-low';
  return 'badge badge-medium';
}

export function priorityLabel(p: string): string {
  const map: Record<string, string> = { high: 'بالا', medium: 'متوسط', low: 'پایین' };
  return map[p] ?? p;
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
