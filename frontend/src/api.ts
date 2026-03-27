export type FlowSummary = {
  dataset: string
  flow_id: string
  flow_dir: string
  num_steps: number
  step_indices: number[]
  website?: string | null
  domain?: string | null
  confirmed_task?: string | null
  candidate_count: number
  gold_count: number
  has_verification_run: boolean
  task?: Record<string, unknown> | null
}

export type FlowStep = {
  dataset: string
  flow_id: string
  step_index: number
  image_name: string
  image_url: string
}

export type ManualVerdictLabel = '' | 'fulfilled' | 'partially_fulfilled' | 'not_fulfilled' | 'abstain'

export type HarvestedRequirement = {
  harvest_id: string
  flow_id: string
  harvested_text: string
  requirement_type: string
  ui_evaluability: string
  non_evaluable_reason: string
  visible_subtype: string
  task_relevance: string
  step_indices: number[]
  rationale?: string
  visible_core_candidate?: string | null
  generation_model?: string
  generation_prompt_path?: string
  confidence?: string
  created_at?: string
}

export type Requirement = {
  requirement_id: string
  flow_id: string
  text: string
  scope: string
  tags: string[]
  origin?: string
  review_status?: string
  step_indices: number[]
  source_candidate_id?: string
  source_harvest_id?: string
  candidate_origin?: string
  benchmark_decision?: string
  parent_harvest_text?: string
  requirement_type?: string
  ui_evaluability?: string
  non_evaluable_reason?: string
  visible_subtype?: string
  task_relevance?: string
  excluded_reason?: string | null
  annotation_notes?: string
  annotated_by?: string
  created_at?: string
  confidence?: string
  rationale?: string
  manual_verification_label?: Exclude<ManualVerdictLabel, ''>
  manual_verification_notes?: string
}

export type EvidenceRef = {
  step_index: number
  evidence_type: string
  reason?: string
}

export type RequirementVerdict = {
  requirement_id: string
  label: string
  evidence: EvidenceRef[]
  confidence?: number
  explanation?: string
}

export type VerificationRun = {
  dataset: string
  flow_id: string
  verifier_name: string
  created_at: string
  verdicts: RequirementVerdict[]
}

export type RequirementPayload = {
  edited_text?: string
  edited_step_indices?: number[]
  edited_tags?: string[]
  annotation_notes?: string
  annotated_by?: string
  manual_verification_label?: Exclude<ManualVerdictLabel, ''>
  manual_verification_notes?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed: ${response.status}`)
  }

  return (await response.json()) as T
}

export function resolveAssetUrl(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  return `${API_BASE}${path}`
}

export const api = {
  listFlows: () => request<FlowSummary[]>('/flows'),
  getFlow: (flowId: string) => request<FlowSummary>(`/flows/${flowId}`),
  getSteps: (flowId: string) => request<FlowStep[]>(`/flows/${flowId}/steps`),
  listHarvested: (flowId: string) => request<HarvestedRequirement[]>(`/flows/${flowId}/harvested`),
  listCandidates: (flowId: string) => request<Requirement[]>(`/flows/${flowId}/candidates`),
  listGold: (flowId: string) => request<Requirement[]>(`/flows/${flowId}/gold`),
  getLatestVerification: (flowId: string) => request<VerificationRun>(`/flows/${flowId}/verification/latest`),
  acceptCandidate: (flowId: string, requirementId: string, payload: RequirementPayload) =>
    request<Requirement>(`/flows/${flowId}/candidates/${requirementId}/accept`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  reviewCandidate: (flowId: string, requirementId: string, payload: RequirementPayload) =>
    request<Requirement>(`/flows/${flowId}/candidates/${requirementId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  rejectCandidate: (flowId: string, requirementId: string, payload: { reason?: string; annotated_by?: string }) =>
    request<Record<string, unknown>>(`/flows/${flowId}/candidates/${requirementId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  markNeedsReview: (flowId: string, requirementId: string) =>
    request<Requirement>(`/flows/${flowId}/candidates/${requirementId}/needs-review`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  updateGoldRequirement: (flowId: string, requirementId: string, payload: RequirementPayload) =>
    request<Requirement>(`/flows/${flowId}/gold/${requirementId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  verify: (payload: { flow_dir: string; max_images: number; dry_run: boolean }) =>
    request<VerificationRun | { status: string; flow_dir: string }>('/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
