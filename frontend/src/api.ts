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
  candidate_id?: string | null
  candidate_source?: string | null
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

export type EvaluationAuditSummary = {
  audit_id: string
  title: string
  created_at: string
  seed: number
  ui_item_count: number
  bbox_item_count: number
  blind_review: boolean
  status: string
}

export type UiEvaluabilityAuditReview = {
  label: string
  rationale: string
  confidence: number
  ambiguous: boolean
  updated_at?: string
}

export type UiEvaluabilityAuditItem = {
  audit_item_id: string
  flow_id: string
  dataset: string
  requirement_id: string
  requirement_text: string
  step_indices: number[]
  manual_label?: string | null
  pipeline_label?: string | null
  labels_match?: boolean
  structural_conflict_reasons?: string[]
  review?: UiEvaluabilityAuditReview | null
}

export type UiEvaluabilityAuditBundle = {
  schema_version: string
  blind: boolean
  seed: number
  sample_size: number
  sampling_note: string
  reviewer_id: string
  items: UiEvaluabilityAuditItem[]
}

export type BoundingBoxAuditReview = {
  applicability: string
  gold_boxes: BoundingBox[]
  evidence_note: string
  gold_locked: boolean
  relevance: string
  sufficiency: string
  error_categories: string[]
  updated_at?: string
}

export type BoundingBoxAuditItem = {
  audit_item_id: string
  dataset: string
  flow_id: string
  requirement_id: string
  requirement_text: string
  claim_id: string
  claim_text: string
  step_index: number
  image_url: string
  image_path: string
  image_width: number
  image_height: number
  image_sha256: string
  coordinate_space: string
  review?: BoundingBoxAuditReview | null
  prediction?: BoundingBoxSuggestion | null
  all_suggestions?: BoundingBoxSuggestion[]
  claim_status?: string | null
  claim_type?: string | null
  inspection_judgment?: {
    status: 'VALID' | 'INCORRECT' | 'UNCERTAIN'
    note: string
    error_category?: 'MISALIGNED' | 'WRONG_LOCATION' | 'SEMANTIC_ERROR' | null
    updated_at?: string
  } | null
  candidate_selection?: OmniParserCandidateSelection | null
}

export type OmniParserCandidate = {
  candidate_id: string
  source: 'omniparser_ui' | 'tesseract_line' | string
  bbox: BoundingBox
  text?: string | null
  caption?: string | null
  associated_text?: string | null
  semantic_text?: string | null
  confidence?: number | null
  rank?: number
  rank_score?: number
  rank_reasons?: string[]
}

export type OmniParserCandidateSelection = OmniParserCandidate & {
  package?: string
  updated_at?: string
}

export type OmniParserCandidateBundle = {
  flow_id: string
  step_index: number
  image_width: number
  image_height: number
  package: string
  ranking_method?: string
  candidates: OmniParserCandidate[]
}

export type BoundingBoxAuditBundle = {
  schema_version: string
  created_at?: string
  source_run_id?: string
  source_run_created_at?: string
  source_run_configuration?: Record<string, unknown>
  blind: boolean
  seed: number
  sample_size: number
  sampling_note: string
  reviewer_id: string
  items: BoundingBoxAuditItem[]
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
  evidence_count?: number
  bbox_evidence_count?: number
  has_pipeline_evidence?: boolean
  has_bbox_evidence?: boolean
}

export type PipelineRunList = {
  flow_id: string
  runs: PipelineRunSummary[]
}

export type UploadedFlowRequirement = {
  requirement_id: string
  flow_id: string
  text: string
  [key: string]: unknown
}

export type CreateUploadedFlowPayload = {
  project_name: string
  description?: string
  requirements_content: string
  requirements_filename?: string
  screenshots: Array<{
    filename: string
    content_base64: string
  }>
}

export type CreateUploadedFlowResponse = {
  flow: FlowSummary
  steps: FlowStep[]
  requirements: UploadedFlowRequirement[]
  requirements_count: number
}

export type StartPipelineRunPayload = {
  verifier: 'deterministic_rule_based' | 'gemini-image'
  verifier_model: string
  retriever: 'lexical'
  requirements_source: 'accepted' | 'benchmark' | 'uploaded'
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
  listEvaluationAudits: () => request<EvaluationAuditSummary[]>('/evaluation-audits'),
  getUiInspectionItems: (auditId: string) =>
    request<UiEvaluabilityAuditBundle>(`/evaluation-audits/${encodeURIComponent(auditId)}/inspection/ui-items`),
  getBboxInspectionItems: (auditId: string) =>
    request<BoundingBoxAuditBundle>(`/evaluation-audits/${encodeURIComponent(auditId)}/inspection/bbox-items`),
  saveBboxInspectionJudgment: (auditId: string, itemId: string, payload: {status: 'VALID' | 'INCORRECT' | 'UNCERTAIN'; note?: string; error_category?: 'MISALIGNED' | 'WRONG_LOCATION' | 'SEMANTIC_ERROR' | null}) =>
    request<{audit_item_id: string; inspection_judgment: NonNullable<BoundingBoxAuditItem['inspection_judgment']>}>(`/evaluation-audits/${encodeURIComponent(auditId)}/inspection/bbox-items/${encodeURIComponent(itemId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  getOmniParserCandidates: (auditId: string, itemId: string) =>
    request<OmniParserCandidateBundle>(`/evaluation-audits/${encodeURIComponent(auditId)}/inspection/bbox-items/${encodeURIComponent(itemId)}/omniparser-candidates`),
  saveOmniParserSelection: (auditId: string, itemId: string, candidateId: string) =>
    request<{audit_item_id: string; candidate_selection: OmniParserCandidateSelection}>(`/evaluation-audits/${encodeURIComponent(auditId)}/inspection/bbox-items/${encodeURIComponent(itemId)}/omniparser-selection`, {
      method: 'PUT',
      body: JSON.stringify({candidate_id: candidateId}),
    }),
  getUiAuditItems: (auditId: string, reviewerId: string) =>
    request<UiEvaluabilityAuditBundle>(`/evaluation-audits/${encodeURIComponent(auditId)}/ui-items?reviewer_id=${encodeURIComponent(reviewerId)}`),
  saveUiAuditReview: (auditId: string, itemId: string, payload: UiEvaluabilityAuditReview & {reviewer_id: string}) =>
    request<{audit_item_id: string; review: UiEvaluabilityAuditReview}>(`/evaluation-audits/${encodeURIComponent(auditId)}/ui-items/${encodeURIComponent(itemId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  getBboxAuditItems: (auditId: string, reviewerId: string) =>
    request<BoundingBoxAuditBundle>(`/evaluation-audits/${encodeURIComponent(auditId)}/bbox-items?reviewer_id=${encodeURIComponent(reviewerId)}`),
  saveBboxAuditReview: (auditId: string, itemId: string, payload: BoundingBoxAuditReview & {reviewer_id: string}) =>
    request<{audit_item_id: string; review: BoundingBoxAuditReview; prediction?: BoundingBoxSuggestion | null}>(`/evaluation-audits/${encodeURIComponent(auditId)}/bbox-items/${encodeURIComponent(itemId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  getEvaluationAuditMetrics: (auditId: string, reviewerId: string) =>
    request<Record<string, unknown>>(`/evaluation-audits/${encodeURIComponent(auditId)}/metrics?reviewer_id=${encodeURIComponent(reviewerId)}`),
  createUploadedFlow: (payload: CreateUploadedFlowPayload) =>
    request<CreateUploadedFlowResponse>('/uploaded-flows', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
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
