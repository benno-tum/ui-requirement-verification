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
  pending_candidate_count?: number
  gold_count: number
  verification_gold_count?: number
  has_verification_run: boolean
  task?: Record<string, unknown> | null
}

export type FlowStep = {
  dataset: string
  flow_id: string
  step_index: number
  image_name: string
  image_url: string
  preview_image_url?: string | null
  original_image_url?: string | null
  image_width?: number | null
  image_height?: number | null
  preview_image_width?: number | null
  preview_image_height?: number | null
  artifact_kind?: string | null
  artifact_label?: string | null
  artifact_page?: number | null
  artifact_context?: string | null
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
  intended_label?: 'fulfilled' | 'partially_fulfilled' | 'not_fulfilled' | 'abstain' | null
  annotation_notes?: string
  annotated_by?: string
  created_at?: string
  confidence?: string
  rationale?: string
  manual_verification_label?: Exclude<ManualVerdictLabel, ''>
  manual_verification_notes?: string
  verification_label?: string | null
  uncertainty_reasons?: string[]
  claims?: VerificationClaim[]
  evidence_steps?: number[]
  evidence_note?: string | null
}

export type EvidenceRef = {
  step_index: number
  evidence_type: string
  bbox?: BoundingBox | null
  matched_text?: string | null
  ui_element_id?: string | null
  reason?: string
  bbox_image_path?: string | null
  bbox_image_width?: number | null
  bbox_image_height?: number | null
  bbox_coordinate_space?: string | null
  bbox_source?: string | null
  bbox_confidence?: number | null
}

export type BoundingBox = {
  x1: number
  y1: number
  x2: number
  y2: number
}

export type EvidenceUnit = {
  step_index: number
  evidence_type: string
  bbox?: BoundingBox | null
  matched_text?: string | null
  ui_element_id?: string | null
  note?: string | null
  bbox_image_path?: string | null
  bbox_image_width?: number | null
  bbox_image_height?: number | null
  bbox_coordinate_space?: string | null
  bbox_source?: string | null
  bbox_confidence?: number | null
}

export type RequirementVerdict = {
  requirement_id: string
  label: string
  evidence: EvidenceRef[]
  confidence?: number
  explanation?: string
}

export type VerificationClaim = {
  claim_id?: string | null
  claim: string
  claim_text?: string
  claim_kind?: string | null
  status: string
  claim_type?: string
  importance?: string
  evidence_steps?: number[]
  evidence_units?: EvidenceUnit[]
  uncertainty_reasons?: string[]
  note?: string
}

export type VerificationGoldItem = {
  requirement_id: string
  flow_id: string
  text: string
  scope: string
  tags: string[]
  source_type?: string | null
  source_id?: string | null
  source_candidate_id?: string | null
  source_harvest_id?: string | null
  step_indices: number[]
  requirement_type?: string | null
  ui_evaluability?: string | null
  visible_subtype?: string | null
  annotation_notes?: string | null
  annotated_by?: string | null
  manual_verification_label?: string | null
  manual_verification_notes?: string | null
  intended_label?: string | null
  verification_label?: string | null
  uncertainty_reasons: string[]
  notes: string[]
  claims: VerificationClaim[]
  evidence_steps: number[]
  evidence_note?: string | null
  rationale?: string | null
  review_status: string
  created_at?: string
  updated_at?: string | null
}

export type RebuildCandidatesResponse = {
  flow_id: string
  candidate_count: number
  requirements: Requirement[]
}

export type RegenerateExpectedClaimsResponse = {
  flow_id: string
  item_count: number
  changed_item_count: number
  changed_claim_count: number
  max_claims: number
  preserve_existing_decisions: boolean
  items: VerificationGoldItem[]
}

export type GenerateHarvestedResponse = {
  flow_id: string
  harvested_count: number
  requirements: HarvestedRequirement[]
}

export type RephraseClaimPayload = {
  requirement_text: string
  claim_text: string
  feedback: string
  claim_status?: string
  claim_type?: string
  importance?: string
}

export type RephraseClaimResponse = {
  claim_text: string
}

export type DecomposeClaimsResponse = {
  claims: VerificationClaim[]
  provider: string
  model_name: string
}

export type VerificationRun = {
  dataset: string
  flow_id: string
  verifier_name: string
  created_at: string
  verdicts: RequirementVerdict[]
}

export type PipelineEvidenceItem = {
  step_index: number
  screenshot_path: string
  visible_observation: string
  bbox?: number[] | BoundingBox | null
  bbox_metadata?: BoundingBoxMetadata | null
  confidence?: number | null
  source?: string | null
  metadata?: {
    bbox_localization?: BoundingBoxMetadata | null
    [key: string]: unknown
  } | null
}

export type BoundingBoxMetadata = {
  image_path?: string | null
  image_width?: number | null
  image_height?: number | null
  coordinate_space?: string | null
  source?: string | null
  confidence?: number | null
  matched_text?: string | null
  score?: number | null
  level?: string | null
}

export type BoundingBoxSuggestion = {
  bbox: BoundingBox
  matched_text: string
  score: number
  confidence?: number | null
  source: string
  level: string
  image_path?: string | null
  image_width?: number | null
  image_height?: number | null
  coordinate_space?: string | null
}

export type BoundingBoxSuggestionResponse = {
  flow_id: string
  step_index: number
  image_path: string
  image_width?: number | null
  image_height?: number | null
  coordinate_space?: string | null
  candidates: BoundingBoxSuggestion[]
}

export type PipelineClaimResult = {
  claim_id: string
  requirement_id: string
  claim_text: string
  status: string
  is_core: boolean
  is_observable: boolean
  evidence: PipelineEvidenceItem[]
  uncertainty_reasons: string[]
  confidence?: number | null
  rationale: string
}

export type PipelineRequirementResult = {
  requirement_id: string
  requirement_text: string
  ui_evaluability: string
  final_label: string
  claims: PipelineClaimResult[]
  evidence: PipelineEvidenceItem[]
  uncertainty_reasons: string[]
  rationale: string
  metadata: Record<string, unknown>
}

export type PipelineVerificationRun = {
  flow_id: string
  results: PipelineRequirementResult[]
  metadata: Record<string, unknown>
}

export type PipelineRunSummary = {
  run_id: string
  flow_id: string
  path: string
  run_name?: string | null
  source: string
  run_folder: string
  timestamp?: string | number | null
  mtime: number
  verifier?: string | null
  verifier_model?: string | null
  retriever?: string | null
  requirements_count: number
  label_distribution: Record<string, number>
  metrics_available: boolean
}

export type PipelineRunList = {
  flow_id: string
  runs: PipelineRunSummary[]
}

export type StartPipelineRunPayload = {
  verifier: 'deterministic_rule_based' | 'gemini-image'
  verifier_model: string
  retriever: 'lexical'
  requirements_source: 'accepted' | 'benchmark'
  top_k: number
  max_images: number
  max_gemini_api_calls: number
  use_cache: boolean
  output_dir_name: string
}

export type PipelineRunJob = {
  job_id: string
  flow_id: string
  status: 'not_started' | 'running' | 'completed' | 'failed'
  output_path?: string | null
  return_code?: number | null
  pid?: number | null
  error?: string | null
  command: string[]
  recent_log_lines: string[]
}

export type RequirementPayload = {
  edited_text?: string
  edited_step_indices?: number[]
  edited_tags?: string[]
  annotation_notes?: string
  annotated_by?: string
  manual_verification_label?: Exclude<ManualVerdictLabel, ''>
  manual_verification_notes?: string
  verification_label?: string
  ui_evaluability?: string
  uncertainty_reasons?: string[]
  claims?: VerificationClaim[]
  evidence_steps?: number[]
  evidence_note?: string
  rationale?: string
  review_status?: string
}

export type VerificationGoldPayload = {
  edited_text?: string
  edited_step_indices?: number[]
  edited_tags?: string[]
  annotation_notes?: string
  annotated_by?: string
  review_status?: string
  verification_label?: string
  ui_evaluability?: string
  uncertainty_reasons?: string[]
  claims?: VerificationClaim[]
  evidence_steps?: number[]
  evidence_note?: string
  rationale?: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

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
    let message = text
    try {
      const parsed = JSON.parse(text) as {detail?: unknown}
      if (typeof parsed.detail === 'string') {
        message = parsed.detail
      }
    } catch {
      // Keep the raw response text.
    }
    throw new ApiError(message || `Request failed: ${response.status}`, response.status)
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
  suggestBoundingBoxes: (flowId: string, payload: { claim_text: string; step_index: number; max_candidates?: number; generate_if_missing?: boolean }) =>
    request<BoundingBoxSuggestionResponse>(`/flows/${flowId}/bbox-suggestions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listHarvested: (flowId: string) => request<HarvestedRequirement[]>(`/flows/${flowId}/harvested`),
  generateHarvestedRequirements: (flowId: string, payload?: { max_images?: number; image_max_side?: number; model_name?: string; temperature?: number }) =>
    request<GenerateHarvestedResponse>(`/flows/${flowId}/harvested/generate`, {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    }),
  listCandidates: (flowId: string) => request<Requirement[]>(`/flows/${flowId}/candidates`),
  rebuildCandidatesFromHarvested: (flowId: string) =>
    request<RebuildCandidatesResponse>(`/flows/${flowId}/candidates/rebuild-from-harvested`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  listGold: (flowId: string) => request<Requirement[]>(`/flows/${flowId}/gold`),
  listVerificationGold: (flowId: string) => request<VerificationGoldItem[]>(`/flows/${flowId}/verification-gold`),
  regenerateExpectedClaims: (flowId: string, payload?: { max_claims?: number; preserve_existing_decisions?: boolean }) =>
    request<RegenerateExpectedClaimsResponse>(`/flows/${flowId}/verification-gold/regenerate-claims`, {
      method: 'POST',
      body: JSON.stringify(payload ?? {}),
    }),
  getLatestVerification: (flowId: string) => request<VerificationRun>(`/flows/${flowId}/verification/latest`),
  getLatestPipelineVerification: (flowId: string) => request<PipelineVerificationRun>(`/flows/${flowId}/verification-pipeline/latest`),
  listPipelineVerificationRuns: (flowId: string) => request<PipelineRunList>(`/flows/${flowId}/verification-pipeline/runs`),
  getPipelineVerificationRun: (flowId: string, runId: string) =>
    request<PipelineVerificationRun>(`/flows/${flowId}/verification-pipeline/run?run_id=${encodeURIComponent(runId)}`),
  startPipelineVerificationRun: (flowId: string, payload: StartPipelineRunPayload) =>
    request<PipelineRunJob>(`/flows/${flowId}/verification-pipeline/start`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getPipelineVerificationJob: (jobId: string) => request<PipelineRunJob>(`/verification-pipeline/jobs/${jobId}`),
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
  updateVerificationGold: (flowId: string, requirementId: string, payload: VerificationGoldPayload) =>
    request<VerificationGoldItem>(`/flows/${flowId}/verification-gold/${requirementId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteGoldRequirement: (flowId: string, requirementId: string) =>
    request<{ flow_id: string; requirement_id: string; deleted: boolean }>(`/flows/${flowId}/gold/${requirementId}`, {
      method: 'DELETE',
    }),
  deleteVerificationGold: (flowId: string, requirementId: string) =>
    request<{ flow_id: string; requirement_id: string; deleted: boolean; deleted_gold_requirement: boolean }>(
      `/flows/${flowId}/verification-gold/${requirementId}`,
      {
        method: 'DELETE',
      },
    ),
  rephraseClaim: (payload: RephraseClaimPayload) =>
    request<RephraseClaimResponse>('/tools/rephrase-claim', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  decomposeClaims: (payload: { requirement_text: string; max_claims?: number }) =>
    request<DecomposeClaimsResponse>('/tools/decompose-claims', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  verify: (payload: { flow_dir: string; max_images: number; dry_run: boolean }) =>
    request<VerificationRun | { status: string; flow_dir: string }>('/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
