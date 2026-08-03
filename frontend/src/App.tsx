import {useEffect, useMemo, useRef, useState, type ReactNode} from 'react'
import {
  ApiError,
  api,
  resolveAssetUrl,
  type BoundingBox,
  type BoundingBoxMetadata,
  type CreateUploadedFlowResponse,
  type BoundingBoxAuditBundle,
  type BoundingBoxAuditItem,
  type OmniParserCandidateBundle,
  type EvidenceUnit,
  type EvaluationAuditSummary,
  type PipelineVerificationRun,
  type PipelineEvidenceItem,
  type PipelineRunJob,
  type PipelineRunSummary,
  type StartPipelineRunPayload,
  type FlowStep,
  type FlowSummary,
  type Requirement,
  type RequirementPayload,
  type UiEvaluabilityAuditBundle,
  type VerificationClaim,
  type VerificationGoldItem,
  type VerificationGoldPayload,
} from './api'

type LoadState = 'idle' | 'loading' | 'error'
type ViewMode = 'overview' | 'verification'
type EditorMode = 'candidate' | 'verification_gold'
type RequirementLike = Requirement | VerificationGoldItem

type EditorState = {
  mode: EditorMode
  requirement: RequirementLike
}

type ClaimFormState = {
  claimId: string
  claim: string
  status: string
  claimType: string
  importance: string
  evidenceSteps: number[]
  evidenceUnit: EvidenceUnit | null
  note: string
  uncertaintyReasons: string[]
}

type PipelineResult = PipelineVerificationRun['results'][number]
type PipelineClaim = PipelineResult['claims'][number]
type ReviewCategoryId =
  | 'all'
  | 'needs_review'
  | 'label_mismatch'
  | 'evidence_no_overlap'
  | 'over_fulfilled'
  | 'should_abstain'
  | 'under_called'
  | 'boundary'
  | 'late_state'
  | 'universal_or_hidden'

type ClaimAlignment = {
  goldClaim: VerificationClaim | null
  predictedClaim: PipelineClaim | null
  score: number
}

type RequirementFormState = {
  text: string
  stepIndices: number[]
  tags: string
  annotationNotes: string
  annotatedBy: string
  reviewStatus: string
  verificationLabel: string
  uiEvaluability: string
  uncertaintyReasons: string[]
  evidenceSteps: number[]
  evidenceNote: string
  rationale: string
  claims: ClaimFormState[]
}

const VIEW_TABS: Array<{id: ViewMode; label: string}> = [
  {id: 'overview', label: 'Overview'},
  {id: 'verification', label: 'Verification run'},
]

const VERIFICATION_LABELS = ['FULFILLED', 'PARTIALLY_FULFILLED', 'NOT_FULFILLED', 'ABSTAIN']
const UI_EVALUABILITY_OPTIONS = ['UI_VERIFIABLE', 'PARTIALLY_UI_VERIFIABLE', 'NOT_UI_VERIFIABLE']
const REVIEW_STATUS_OPTIONS = ['needs_review', 'accepted']
const UNCERTAINTY_REASON_OPTIONS = [
  'TEXTUAL_AMBIGUITY',
  'SCOPE_OR_CONTEXT_AMBIGUITY',
  'QUANTIFIER_OR_COMPLETENESS_AMBIGUITY',
  'EVIDENCE_INTERPRETATION_AMBIGUITY',
  'FLOW_COVERAGE_GAP',
  'UNVERIFIED_SYSTEM_OUTCOME',
  'NONTRIVIAL_HIDDEN_PROPERTY',
]
const CLAIM_STATUS_OPTIONS = ['SUPPORTED', 'SUPPORTED_WITH_CAVEAT', 'CONTRADICTED', 'MISSING', 'HIDDEN', 'AMBIGUOUS', 'OUT_OF_SCOPE']
const CLAIM_TYPE_OPTIONS = ['OBSERVABLE', 'HIDDEN']
const CLAIM_IMPORTANCE_OPTIONS = ['CORE', 'SUPPORTING']
const REVIEW_CATEGORY_OPTIONS: Array<{id: ReviewCategoryId; label: string}> = [
  {id: 'evidence_no_overlap', label: 'No evidence overlap'},
  {id: 'over_fulfilled', label: 'Over-fulfilled'},
  {id: 'should_abstain', label: 'Should abstain'},
  {id: 'under_called', label: 'Under-called'},
  {id: 'boundary', label: 'Boundary'},
  {id: 'late_state', label: 'Late state'},
  {id: 'universal_or_hidden', label: 'Universal/hidden'},
  {id: 'label_mismatch', label: 'Any label mismatch'},
]

const GEMINI_VERIFIER_MODELS = [
  {value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash-Lite (recommended)'},
  {value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash-Lite (lowest cost)'},
  {value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash'},
  {value: 'gemini-3.6-flash', label: 'Gemini 3.6 Flash (stronger)'},
  {value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro Preview (historical)'},
]

const TEXT_MODELS_BY_PROVIDER: Record<'gemini' | 'deepseek', Array<{value: string; label: string}>> = {
  gemini: [
    {value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash-Lite'},
    {value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash-Lite'},
    {value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash'},
    {value: 'gemini-3.6-flash', label: 'Gemini 3.6 Flash'},
  ],
  deepseek: [
    {value: 'deepseek-chat', label: 'DeepSeek Chat'},
    {value: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash'},
    {value: 'deepseek-v4-pro', label: 'DeepSeek V4 Pro'},
  ],
}

function defaultTextModel(provider: 'gemini' | 'deepseek'): string {
  return TEXT_MODELS_BY_PROVIDER[provider][0].value
}

type AppRoute = 'workbench' | 'upload' | 'evaluation'
const HISTORICAL_EVALUATION_INSPECTION_ENABLED = false

function routeFromLocation(): AppRoute {
  if (window.location.pathname.startsWith('/verify/new')) return 'upload'
  if (HISTORICAL_EVALUATION_INSPECTION_ENABLED && window.location.pathname.startsWith('/evaluation')) return 'evaluation'
  return 'workbench'
}

function App() {
  const [route, setRoute] = useState<AppRoute>(routeFromLocation)

  useEffect(() => {
    const handlePopState = () => setRoute(routeFromLocation())
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  function navigate(nextRoute: AppRoute, flowId?: string) {
    const path = nextRoute === 'upload'
      ? `/verify/new${flowId ? `?flow_id=${encodeURIComponent(flowId)}` : ''}`
      : nextRoute === 'evaluation'
        ? '/evaluation'
        : '/'
    window.history.pushState({}, '', path)
    setRoute(nextRoute)
  }

  if (route === 'upload') {
    return <UploadVerificationPage onBack={() => navigate('workbench')} onProjectCreated={(flowId) => navigate('upload', flowId)} />
  }
  if (HISTORICAL_EVALUATION_INSPECTION_ENABLED && route === 'evaluation') {
    return <EvaluationAuditPage onBack={() => navigate('workbench')} />
  }
  return <AnnotationWorkbench onOpenUpload={() => navigate('upload')} onOpenEvaluation={() => navigate('evaluation')} />
}

const THESIS_PURE_FLOW_IDS = new Set([
  'pure_2010_mashboot',
  'pure_2010_split_merge',
])

function isThesisEvaluationFlow(flow: FlowSummary): boolean {
  if (flow.dataset === 'pure') {
    return THESIS_PURE_FLOW_IDS.has(flow.flow_id)
  }

  const match = /^(\d{2})_/.exec(flow.flow_id)
  if (flow.dataset !== 'mind2web' || !match) return false
  const flowNumber = Number(match[1])
  return flowNumber >= 1 && flowNumber <= 13
}

function AnnotationWorkbench({onOpenUpload, onOpenEvaluation}: {onOpenUpload: () => void; onOpenEvaluation: () => void}) {
  const [flows, setFlows] = useState<FlowSummary[]>([])
  const [flowsState, setFlowsState] = useState<LoadState>('idle')
  const [selectedFlowId, setSelectedFlowId] = useState<string>('')
  const [selectedFlow, setSelectedFlow] = useState<FlowSummary | null>(null)
  const [steps, setSteps] = useState<FlowStep[]>([])
  const [candidates, setCandidates] = useState<Requirement[]>([])
  const [verificationGold, setVerificationGold] = useState<VerificationGoldItem[]>([])
  const [pipelineRun, setPipelineRun] = useState<PipelineVerificationRun | null>(null)
  const [detailsState, setDetailsState] = useState<LoadState>('idle')
  const [message, setMessage] = useState<string>('')
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
  const [highlightedStep, setHighlightedStep] = useState<number | null>(null)
  const [zoomStep, setZoomStep] = useState<FlowStep | null>(null)
  const [editor, setEditor] = useState<EditorState | null>(null)
  const [reviewCursor, setReviewCursor] = useState<EditorState | null>(null)
  const [openNextAfterSave, setOpenNextAfterSave] = useState<boolean>(false)
  const [regeneratingClaims, setRegeneratingClaims] = useState<boolean>(false)

  useEffect(() => {
    void loadFlows()
  }, [])

  useEffect(() => {
    if (!selectedFlowId) {
      return
    }
    void loadFlowDetails(selectedFlowId)
  }, [selectedFlowId])

  useEffect(() => {
    if (highlightedStep === null) {
      return
    }
    const timeout = window.setTimeout(() => setHighlightedStep(null), 1800)
    return () => window.clearTimeout(timeout)
  }, [highlightedStep])

  async function loadFlows() {
    setFlowsState('loading')
    try {
      const data = (await api.listFlows()).filter(isThesisEvaluationFlow)
      setFlows(data)
      setFlowsState('idle')
      if (data.length === 0) {
        setSelectedFlowId('')
        return
      }
      if (!selectedFlowId || !data.some((flow) => flow.flow_id === selectedFlowId)) {
        setSelectedFlowId(data[0].flow_id)
      }
    } catch (error) {
      setFlowsState('error')
      setMessage(error instanceof Error ? error.message : 'Failed to load flows')
    }
  }

  async function loadFlowDetails(flowId: string) {
    setDetailsState('loading')
    setMessage('')
    setSelectedFlow(null)
    setSteps([])
    setCandidates([])
    setVerificationGold([])
    setPipelineRun(null)

    try {
      const flow = await api.getFlow(flowId)
      setSelectedFlow(flow)

      const [stepsResult, candidatesResult, verificationGoldResult, pipelineRunResult] = await Promise.allSettled([
        api.getSteps(flowId),
        api.listCandidates(flowId),
        api.listVerificationGold(flowId),
        api.getLatestPipelineVerification(flowId),
      ])

      if (stepsResult.status === 'fulfilled') {
        setSteps(stepsResult.value)
      }
      if (candidatesResult.status === 'fulfilled') {
        setCandidates(candidatesResult.value)
      }
      if (verificationGoldResult.status === 'fulfilled') {
        setVerificationGold(verificationGoldResult.value)
      }
      if (pipelineRunResult.status === 'fulfilled') {
        setPipelineRun(pipelineRunResult.value)
      }

      setDetailsState('idle')
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        const data = (await api.listFlows()).filter(isThesisEvaluationFlow)
        setFlows(data)
        const fallback = data.find((flow) => flow.flow_id !== flowId) ?? data[0]
        setSelectedFlowId(fallback?.flow_id ?? '')
        setDetailsState('idle')
        setMessage(fallback ? `Flow ${flowId} no longer exists. Switched to ${fallback.flow_id}.` : `Flow ${flowId} no longer exists.`)
        return
      }
      setDetailsState('error')
      setMessage(error instanceof Error ? error.message : 'Failed to load flow details')
    }
  }

  function jumpToStep(stepIndex: number) {
    setHighlightedStep(stepIndex)
    const element = document.getElementById(`step-${stepIndex}`)
    if (element) {
      element.scrollIntoView({behavior: 'smooth', block: 'start'})
    }
  }

  async function handleCandidateAction(action: 'accept' | 'reject' | 'needs_review', requirement: Requirement) {
    if (!selectedFlowId) {
      return
    }
    setMessage('')
    try {
      if (action === 'accept') {
        await api.acceptCandidate(selectedFlowId, requirement.requirement_id, {})
      } else if (action === 'reject') {
        await api.rejectCandidate(selectedFlowId, requirement.requirement_id, {})
      } else {
        await api.markNeedsReview(selectedFlowId, requirement.requirement_id)
        setEditor({mode: 'candidate', requirement: {...requirement, review_status: 'needs_review'}})
      }
      await loadFlowDetails(selectedFlowId)
      setMessage(`${requirement.requirement_id} updated.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to update candidate')
    }
  }

  async function handleSaveEditor(
    action: 'review' | 'promote' | 'save_verification_gold',
    payload: RequirementPayload | VerificationGoldPayload,
    openNext = false,
  ) {
    if (!selectedFlowId || !editor) {
      return
    }

    setMessage('')
    const requirementId = editor.requirement.requirement_id

    try {
      if (editor.mode === 'candidate' && action === 'review') {
        await api.reviewCandidate(selectedFlowId, requirementId, payload as RequirementPayload)
        setMessage(`${requirementId} saved for review.`)
      } else if (editor.mode === 'candidate' && action === 'promote') {
        await api.acceptCandidate(selectedFlowId, requirementId, payload as RequirementPayload)
        setMessage(`${requirementId} promoted to gold.`)
      } else if (editor.mode === 'verification_gold' && action === 'save_verification_gold') {
        await api.updateVerificationGold(selectedFlowId, requirementId, payload as VerificationGoldPayload)
        setMessage(`${requirementId} verification benchmark item updated.`)
      }

      setReviewCursor(editor)
      setEditor(null)
      await loadFlowDetails(selectedFlowId)
      if (openNext) {
        setOpenNextAfterSave(true)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save requirement changes'
      setMessage(errorMessage)
      window.alert(errorMessage)
    }
  }

  async function handleDeleteGoldRequirement(requirement: VerificationGoldItem) {
    if (!selectedFlowId) {
      return
    }

    const confirmed = window.confirm(`Delete requirement ${requirement.requirement_id} from the verification benchmark?`)
    if (!confirmed) {
      return
    }

    setMessage('')
    try {
      const result = await api.deleteVerificationGold(selectedFlowId, requirement.requirement_id)
      await loadFlowDetails(selectedFlowId)
      setEditor(null)
      setMessage(
        result.deleted_gold_requirement
          ? `${requirement.requirement_id} deleted from verification benchmark and gold requirements.`
          : `${requirement.requirement_id} deleted from verification benchmark.`,
      )
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to delete gold requirement')
    }
  }


  async function handleRegenerateExpectedClaims() {
    if (!selectedFlowId || regeneratingClaims) {
      return
    }

    const confirmed = window.confirm(
      'Regenerate expected claims for all verification benchmark items in this flow? Existing claim statuses and evidence will be preserved by claim position.',
    )
    if (!confirmed) {
      return
    }

    setMessage('')
    setRegeneratingClaims(true)
    try {
      const result = await api.regenerateExpectedClaims(selectedFlowId, {
        max_claims: 4,
        preserve_existing_decisions: true,
      })
      setVerificationGold(result.items)
      await loadFlowDetails(selectedFlowId)
      setEditor(null)
      setMessage(`Regenerated expected claims for ${result.changed_item_count} items (${result.changed_claim_count} claim changes).`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to regenerate expected claims')
    } finally {
      setRegeneratingClaims(false)
    }
  }

  async function handleAcceptVerificationGoldFromPipeline(requirement: VerificationGoldItem) {
    if (!selectedFlowId) {
      return
    }

    setMessage('')
    try {
      const updated = await api.updateVerificationGold(selectedFlowId, requirement.requirement_id, {
        review_status: 'accepted',
      })
      setVerificationGold((items) =>
        items.map((item) => (item.requirement_id === updated.requirement_id ? updated : item)),
      )
      setMessage(`${updated.requirement_id} accepted.`)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to accept verification benchmark item'
      setMessage(errorMessage)
      window.alert(errorMessage)
      throw error
    }
  }

  const representedCandidateIds = useMemo(() => candidateIdsRepresentedInVerificationGold(verificationGold), [verificationGold])
  const activeCandidates = useMemo(
    () =>
      candidates.filter(
        (candidate) =>
          candidate.review_status !== 'accepted' &&
          candidate.review_status !== 'rejected' &&
          !representedCandidateIds.has(candidate.requirement_id),
      ),
    [candidates, representedCandidateIds],
  )
  const orderedVerificationGold = useMemo(() => orderReviewItemsFirst(verificationGold), [verificationGold])
  function openNextNeedsReviewItem() {
    const currentPosition = editor ?? reviewCursor
    const currentRequirementId = currentPosition?.requirement.requirement_id
    const currentMode = currentPosition?.mode
    const reviewGold = orderedVerificationGold.filter((item) => item.review_status === 'needs_review')
    const reviewCandidates = activeCandidates.filter((candidate) => candidate.review_status === 'needs_review')

    if (reviewGold.length > 0) {
      const currentIndex =
        currentMode === 'verification_gold'
          ? reviewGold.findIndex((item) => item.requirement_id === currentRequirementId)
          : -1
      const nextGold = reviewGold[currentIndex >= 0 ? (currentIndex + 1) % reviewGold.length : 0]
      setViewMode('overview')
      setEditor({mode: 'verification_gold', requirement: nextGold})
      return
    }

    if (reviewCandidates.length > 0) {
      const currentIndex =
        currentMode === 'candidate'
          ? reviewCandidates.findIndex((item) => item.requirement_id === currentRequirementId)
          : -1
      const nextCandidate = reviewCandidates[currentIndex >= 0 ? (currentIndex + 1) % reviewCandidates.length : 0]
      setViewMode('overview')
      setEditor({mode: 'candidate', requirement: nextCandidate})
      return
    }

    setMessage('No needs review verification or candidate items left.')
  }

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Enter' && event.metaKey && event.shiftKey && editor === null) {
        event.preventDefault()
        openNextNeedsReviewItem()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeCandidates, editor, orderedVerificationGold, reviewCursor])

  useEffect(() => {
    if (!openNextAfterSave || editor !== null || detailsState === 'loading') {
      return
    }
    setOpenNextAfterSave(false)
    openNextNeedsReviewItem()
  }, [activeCandidates, detailsState, editor, openNextAfterSave, orderedVerificationGold])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>UI Verifier</h1>
          <p>Annotation workbench</p>
        </div>

        <button className="secondary-button" onClick={() => void loadFlows()}>
          Refresh flows
        </button>

        <button className="upload-route-button" onClick={onOpenUpload}>
          <span>＋</span>
          New screenshot verification
        </button>

        {HISTORICAL_EVALUATION_INSPECTION_ENABLED && (
          <button className="secondary-button audit-route-button" onClick={onOpenEvaluation}>
            Historical evaluation inspection (optional)
          </button>
        )}

        <p className="dataset-availability-note">
          PURE source data can be installed separately, but PURE screenshot flows and verification runs are not included in the public viewer.
        </p>

        <div className="flow-list">
          {flowsState === 'loading' && <p>Loading flows...</p>}
          {flows.map((flow) => (
            <button
              key={flow.flow_id}
              className={flow.flow_id === selectedFlowId ? 'flow-item active' : 'flow-item'}
              onClick={() => setSelectedFlowId(flow.flow_id)}
            >
              <strong>{flow.flow_id}</strong>
              <span>{flow.website ?? flow.dataset}</span>
              <span>{flow.num_steps} steps</span>
              <span>
                {flow.gold_count} accepted reqs · {flow.verification_gold_count ?? 0} verification items
              </span>
            </button>
          ))}
        </div>
      </aside>

      <main className="main-content">
        <section className="topbar card">
          <div>
            <h2>{selectedFlow?.flow_id ?? 'Select a flow'}</h2>
            <p>{selectedFlow?.confirmed_task ?? 'No task loaded yet.'}</p>
          </div>
        </section>

        <section className="card tab-card">
          <div className="tab-row">
            {VIEW_TABS.map((tab) => (
              <button
                key={tab.id}
                className={viewMode === tab.id ? 'tab-button active' : 'tab-button'}
                onClick={() => setViewMode(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </section>

        {message && <section className="message card">{message}</section>}
        {detailsState === 'loading' && <section className="card">Loading flow details...</section>}

        {selectedFlow && viewMode === 'overview' && (
          <OverviewPanel
            steps={steps}
            activeCandidates={activeCandidates}
            gold={orderedVerificationGold}
            onJumpToStep={jumpToStep}
            onOpenZoom={setZoomStep}
            onPromote={(requirement) => void handleCandidateAction('accept', requirement)}
            onEditCandidate={(requirement) => setEditor({mode: 'candidate', requirement})}
            onReject={(requirement) => void handleCandidateAction('reject', requirement)}
            onEditGold={(requirement) => setEditor({mode: 'verification_gold', requirement})}
            onDeleteGold={(requirement) => void handleDeleteGoldRequirement(requirement)}
            onRegenerateExpectedClaims={() => void handleRegenerateExpectedClaims()}
            regeneratingClaims={regeneratingClaims}
          />
        )}

        {selectedFlow && viewMode === 'verification' && (
          <VerificationRunPanel
            flowId={selectedFlow.flow_id}
            steps={steps}
            pipelineRun={pipelineRun}
            verificationGold={verificationGold}
            defaultRequirementsSource={selectedFlow.dataset === 'uploads' ? 'uploaded' : 'benchmark'}
            onJumpToStep={jumpToStep}
            onEditVerificationGold={(requirement) => setEditor({mode: 'verification_gold', requirement})}
            onAcceptVerificationGold={(requirement) => handleAcceptVerificationGoldFromPipeline(requirement)}
          />
        )}

        <footer className="footer-note card">
          <strong>{activeCandidates.length}</strong> candidate requirements still need review.{' '}
          <strong>{verificationGold.filter((item) => item.review_status !== 'accepted').length}</strong> verification benchmark items are still drafts.
        </footer>
      </main>

      {zoomStep && <ImageLightbox step={zoomStep} onClose={() => setZoomStep(null)} />}
      {editor && (
        <RequirementEditorModal
          mode={editor.mode}
          requirement={editor.requirement}
          availableSteps={steps}
          defaultAnnotatedBy="benno"
          onClose={() => setEditor(null)}
          onSave={(action, payload, openNext) => void handleSaveEditor(action, payload, openNext)}
          onDelete={
            editor.mode === 'candidate'
              ? (requirement) => {
                  if (window.confirm(`Delete candidate requirement ${requirement.requirement_id}?`)) {
                    void handleCandidateAction('reject', requirement as Requirement)
                  }
                }
              : (requirement) => void handleDeleteGoldRequirement(requirement as VerificationGoldItem)
          }
        />
      )}
    </div>
  )
}

type AuditMode = 'ui' | 'bbox'
type BboxDisplayRegion = {bbox: BoundingBox; label: string; items: BoundingBoxAuditItem[]}
type BboxRequirementGroup = {
  key: string
  flowId: string
  requirementId: string
  requirementText: string
  claims: Array<{claimId: string; text: string; status: string | null}>
  screens: Array<{
    stepIndex: number
    item: BoundingBoxAuditItem
    items: BoundingBoxAuditItem[]
    regions: BboxDisplayRegion[]
  }>
  omittedScreens: number
}

function normalizedRegionKey(item: BoundingBoxAuditItem): string {
  if (!item.prediction || item.image_width <= 0 || item.image_height <= 0) return `${item.claim_id}:missing`
  const box = item.prediction.bbox
  const normalized = [
    box.x1 / item.image_width,
    box.y1 / item.image_height,
    box.x2 / item.image_width,
    box.y2 / item.image_height,
  ].map((value) => value.toFixed(3)).join(',')
  return `${item.claim_id}:${normalized}`
}

function shortClaimLabel(claimId: string): string {
  const match = claimId.match(/-C\d+$/)
  return match ? match[0].slice(1) : claimId
}

function mergeAdjacentOcrRegions(regions: BboxDisplayRegion[], imageWidth: number, imageHeight: number): BboxDisplayRegion[] {
  const pending = regions.map((region) => ({...region, items: [...region.items]}))
  const verticalGapLimit = Math.max(14, imageHeight * 0.008)
  const horizontalGapLimit = Math.max(18, imageWidth * 0.015)
  let changed = true
  while (changed) {
    changed = false
    for (let leftIndex = 0; leftIndex < pending.length && !changed; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < pending.length; rightIndex += 1) {
        const left = pending[leftIndex]
        const right = pending[rightIndex]
        const leftClaims = [...new Set(left.items.map((item) => item.claim_id))].sort().join('|')
        const rightClaims = [...new Set(right.items.map((item) => item.claim_id))].sort().join('|')
        const allOcr = [...left.items, ...right.items].every((item) => item.prediction?.candidate_source === 'tesseract_line')
        if (!allOcr || leftClaims !== rightClaims) continue
        const horizontalOverlap = left.bbox.x1 < right.bbox.x2 && left.bbox.x2 > right.bbox.x1
        const verticalOverlap = left.bbox.y1 < right.bbox.y2 && left.bbox.y2 > right.bbox.y1
        const verticalGap = Math.max(0, Math.max(left.bbox.y1, right.bbox.y1) - Math.min(left.bbox.y2, right.bbox.y2))
        const horizontalGap = Math.max(0, Math.max(left.bbox.x1, right.bbox.x1) - Math.min(left.bbox.x2, right.bbox.x2))
        if (!((horizontalOverlap && verticalGap <= verticalGapLimit) || (verticalOverlap && horizontalGap <= horizontalGapLimit))) continue
        pending[leftIndex] = {
          bbox: {
            x1: Math.min(left.bbox.x1, right.bbox.x1),
            y1: Math.min(left.bbox.y1, right.bbox.y1),
            x2: Math.max(left.bbox.x2, right.bbox.x2),
            y2: Math.max(left.bbox.y2, right.bbox.y2),
          },
          label: [...new Set([...left.items, ...right.items].map((item) => item.claim_id))].map(shortClaimLabel).join('+'),
          items: [...left.items, ...right.items],
        }
        pending.splice(rightIndex, 1)
        changed = true
        break
      }
    }
  }
  return pending
}

function groupBboxItemsByRequirement(items: BoundingBoxAuditItem[]): BboxRequirementGroup[] {
  const requirementItems = new Map<string, BoundingBoxAuditItem[]>()
  for (const item of items) {
    const key = `${item.flow_id}:${item.requirement_id}`
    requirementItems.set(key, [...(requirementItems.get(key) ?? []), item])
  }
  return [...requirementItems.entries()].map(([key, groupedItems]) => {
    const first = groupedItems[0]
    const claims = new Map<string, {claimId: string; text: string; status: string | null}>()
    const byStep = new Map<number, BoundingBoxAuditItem[]>()
    for (const item of groupedItems) {
      claims.set(item.claim_id, {claimId: item.claim_id, text: item.claim_text, status: item.claim_status ?? null})
      byStep.set(item.step_index, [...(byStep.get(item.step_index) ?? []), item])
    }
    const seenScreenSignatures = new Set<string>()
    let omittedScreens = 0
    const screens: BboxRequirementGroup['screens'] = []
    for (const [stepIndex, screenItems] of [...byStep.entries()].sort((left, right) => left[0] - right[0])) {
      const screenSignature = screenItems.map(normalizedRegionKey).sort().join('|')
      if (seenScreenSignatures.has(screenSignature)) {
        omittedScreens += 1
        continue
      }
      seenScreenSignatures.add(screenSignature)
      const regionItems = new Map<string, {bbox: BoundingBox; items: BoundingBoxAuditItem[]}>()
      for (const item of screenItems) {
        if (!item.prediction) continue
        const boxKey = normalizedRegionKey({...item, claim_id: ''})
        const existing = regionItems.get(boxKey)
        if (existing) {
          existing.items.push(item)
        } else {
          regionItems.set(boxKey, {bbox: item.prediction.bbox, items: [item]})
        }
      }
      const exactRegions = [...regionItems.values()].map((region) => ({
        bbox: region.bbox,
        label: [...new Set(region.items.map((item) => item.claim_id))].map(shortClaimLabel).join('+'),
        items: region.items,
      }))
      screens.push({
        stepIndex,
        item: screenItems[0],
        items: screenItems,
        regions: mergeAdjacentOcrRegions(exactRegions, screenItems[0].image_width, screenItems[0].image_height),
      })
    }
    return {
      key,
      flowId: first.flow_id,
      requirementId: first.requirement_id,
      requirementText: first.requirement_text,
      claims: [...claims.values()].sort((left, right) => left.claimId.localeCompare(right.claimId, undefined, {numeric: true})),
      screens,
      omittedScreens,
    }
  }).sort((left, right) => {
    const flowOrder = left.flowId.localeCompare(right.flowId, undefined, {numeric: true})
    if (flowOrder) return flowOrder
    const leftContrastive = left.requirementId.startsWith('CONTR-') ? 1 : 0
    const rightContrastive = right.requirementId.startsWith('CONTR-') ? 1 : 0
    if (leftContrastive !== rightContrastive) return leftContrastive - rightContrastive
    return left.requirementId.localeCompare(right.requirementId, undefined, {numeric: true})
  })
}

function EvaluationAuditPage({onBack}: {onBack: () => void}) {
  const [audits, setAudits] = useState<EvaluationAuditSummary[]>([])
  const [selectedAuditId, setSelectedAuditId] = useState('')
  const [mode, setMode] = useState<AuditMode>('ui')
  const [uiBundle, setUiBundle] = useState<UiEvaluabilityAuditBundle | null>(null)
  const [bboxBundle, setBboxBundle] = useState<BoundingBoxAuditBundle | null>(null)
  const [uiFilter, setUiFilter] = useState<'differences' | 'all' | 'matches'>('differences')
  const [bboxFilter, setBboxFilter] = useState<'all' | 'incorrect' | 'missing' | 'low_score'>('all')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [savingBoxIds, setSavingBoxIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    void api.listEvaluationAudits().then((items) => {
      setAudits(items)
      if (items.length > 0) setSelectedAuditId((current) => current || items[0].audit_id)
    }).catch((error) => setMessage(error instanceof Error ? error.message : 'Failed to load evaluation audits'))
  }, [])

  useEffect(() => {
    if (!selectedAuditId) return
    setLoading(true)
    Promise.all([
      api.getUiInspectionItems(selectedAuditId),
      api.getBboxInspectionItems(selectedAuditId),
    ]).then(([ui, bbox]) => {
      setUiBundle(ui)
      setBboxBundle(bbox)
      setMessage('')
    }).catch((error) => setMessage(error instanceof Error ? error.message : 'Failed to load inspection data')).finally(() => setLoading(false))
  }, [selectedAuditId])

  const uiItems = (uiBundle?.items ?? []).filter((item) =>
    uiFilter === 'all' || (uiFilter === 'matches' ? item.labels_match : !item.labels_match),
  )
  const bboxItems = (bboxBundle?.items ?? []).filter((item) => {
    if (bboxFilter === 'incorrect') return item.inspection_judgment?.status === 'INCORRECT'
    if (bboxFilter === 'missing') return !item.prediction
    if (bboxFilter === 'low_score') return item.prediction != null && item.prediction.score < 0.25
    return true
  })
  const bboxRequirementGroups = useMemo(() => groupBboxItemsByRequirement(bboxItems), [bboxItems])
  const matchCount = uiBundle?.items.filter((item) => item.labels_match).length ?? 0
  const differenceCount = (uiBundle?.items.length ?? 0) - matchCount
  const boxCount = bboxBundle?.items.filter((item) => item.prediction).length ?? 0
  const incorrectBoxCount = bboxBundle?.items.filter((item) => item.inspection_judgment?.status === 'INCORRECT').length ?? 0

  async function saveBboxJudgment(item: BoundingBoxAuditItem, status: 'VALID' | 'INCORRECT' | 'UNCERTAIN', note: string) {
    try {
      const response = await api.saveBboxInspectionJudgment(selectedAuditId, item.audit_item_id, {status, note})
      setBboxBundle((current) => current ? {
        ...current,
        items: current.items.map((candidate) => candidate.audit_item_id === item.audit_item_id
          ? {...candidate, inspection_judgment: response.inspection_judgment}
          : candidate),
      } : current)
      setMessage(`Marked ${item.claim_id} as ${humanizeStatus(status)}.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to save bounding-box judgment')
    }
  }

  async function judgeBboxRegion(
    items: BoundingBoxAuditItem[],
    status: 'VALID' | 'INCORRECT',
    errorCategory: 'MISALIGNED' | 'WRONG_LOCATION' | 'SEMANTIC_ERROR' | null = null,
    note?: string,
  ) {
    const pending = items.filter((item) =>
      item.inspection_judgment?.status !== status
      || (status === 'INCORRECT' && item.inspection_judgment?.error_category !== errorCategory)
      || (note !== undefined && item.inspection_judgment?.note !== note),
    )
    if (pending.length === 0) return
    const pendingIds = new Set(pending.map((item) => item.audit_item_id))
    setSavingBoxIds((current) => new Set([...current, ...pendingIds]))
    try {
      const saved = []
      for (const item of pending) {
        saved.push(await api.saveBboxInspectionJudgment(selectedAuditId, item.audit_item_id, {
          status,
          note: note ?? item.inspection_judgment?.note ?? '',
          error_category: status === 'INCORRECT' ? errorCategory : null,
        }))
      }
      const judgments = new Map(saved.map((response) => [response.audit_item_id, response.inspection_judgment]))
      setBboxBundle((current) => current ? {
        ...current,
        items: current.items.map((candidate) => judgments.has(candidate.audit_item_id)
          ? {...candidate, inspection_judgment: judgments.get(candidate.audit_item_id)}
          : candidate),
      } : current)
      const claims = [...new Set(pending.map((item) => item.claim_id))].join(', ')
      setMessage(status === 'VALID' ? `Accepted bounding box for ${claims}.` : `Marked bounding box as incorrect for ${claims}.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to save bounding-box judgment')
    } finally {
      setSavingBoxIds((current) => {
        const next = new Set(current)
        pendingIds.forEach((id) => next.delete(id))
        return next
      })
    }
  }

  async function saveCandidateSelection(item: BoundingBoxAuditItem, candidateId: string) {
    setSavingBoxIds((current) => new Set([...current, item.audit_item_id]))
    try {
      const response = await api.saveOmniParserSelection(selectedAuditId, item.audit_item_id, candidateId)
      setBboxBundle((current) => current ? {
        ...current,
        items: current.items.map((candidate) => candidate.audit_item_id === item.audit_item_id
          ? {...candidate, candidate_selection: response.candidate_selection}
          : candidate),
      } : current)
      setMessage(`Saved ${response.candidate_selection.candidate_id} as the local candidate for ${item.claim_id}.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to save OmniParser candidate')
    } finally {
      setSavingBoxIds((current) => {
        const next = new Set(current)
        next.delete(item.audit_item_id)
        return next
      })
    }
  }

  return (
    <div className="audit-page">
      <header className="upload-nav">
        <button className="brand-button" onClick={onBack} aria-label="Back to annotation workbench">
          <span className="brand-mark">UV</span>
          <span><strong>Evidence inspection</strong><small>Quick comparison and acceptance workspace</small></span>
        </button>
        <button className="secondary-button" onClick={onBack}>Back to workbench</button>
      </header>

      <main className="audit-main">
        <section className="card audit-toolbar">
          <div>
            <span className="eyebrow">Quick visual audit</span>
            <h1>Compare labels and inspect bounding boxes</h1>
            <p>No relabeling is required. Manual UI-verifiability labels are treated as the reference, and the selected inspection dataset's pipeline regions are shown directly.</p>
          </div>
          <div className="toolbar-grid audit-controls">
            <label>Audit<select value={selectedAuditId} onChange={(event) => setSelectedAuditId(event.target.value)}>{audits.map((audit) => <option key={audit.audit_id} value={audit.audit_id}>{audit.title}</option>)}</select></label>
            <Metric label="UI matches" value={`${matchCount} / ${uiBundle?.items.length ?? 0}`} />
            <Metric label="UI differences" value={String(differenceCount)} />
            <Metric label="Boxes / incorrect" value={`${boxCount} / ${incorrectBoxCount}`} />
          </div>
          <div className="tab-row">
            <button className={mode === 'ui' ? 'tab-button active' : 'tab-button'} onClick={() => setMode('ui')}>UI-verifiability comparison</button>
            <button className={mode === 'bbox' ? 'tab-button active' : 'tab-button'} onClick={() => setMode('bbox')}>Bounding-box gallery</button>
          </div>
        </section>
        {message && <section className="message card">{message}</section>}
        {loading && <section className="card">Loading inspection data…</section>}

        {!loading && mode === 'ui' && (
          <section className="inspection-section">
            <div className="card inspection-filter-row">
              <strong>Show</strong>
              {(['differences', 'all', 'matches'] as const).map((filter) => <button key={filter} className={uiFilter === filter ? 'tab-button active' : 'tab-button'} onClick={() => setUiFilter(filter)}>{humanizeStatus(filter)}</button>)}
              <span>{uiItems.length} requirements</span>
            </div>
            <div className="ui-comparison-list">
              {uiItems.map((item) => (
                <article className={`card ui-comparison-card ${item.labels_match ? 'match' : 'difference'}`} key={item.audit_item_id}>
                  <div className="panel-header"><div><h3>{item.requirement_id}</h3><span>{item.flow_id} · {item.dataset}</span></div><span className={`comparison-result ${item.labels_match ? 'match' : 'difference'}`}>{item.labels_match ? 'Match' : 'Different'}</span></div>
                  <p>{item.requirement_text}</p>
                  <div className="label-comparison-grid">
                    <div><small>Manual reference</small><span className={`status-pill ${statusClass(item.manual_label)}`}>{humanizeStatus(item.manual_label)}</span></div>
                    <div><small>Pipeline classifier</small><span className={`status-pill ${statusClass(item.pipeline_label)}`}>{humanizeStatus(item.pipeline_label)}</span></div>
                  </div>
                  {(item.structural_conflict_reasons?.length ?? 0) > 0 && <p className="helper-text">Audit signal: {item.structural_conflict_reasons?.map(humanizeStatus).join(', ')}</p>}
                </article>
              ))}
            </div>
          </section>
        )}

        {!loading && mode === 'bbox' && (
          <section className="inspection-section">
            <div className="card inspection-filter-row">
              <strong>Show</strong>
              {(['all', 'incorrect', 'missing', 'low_score'] as const).map((filter) => <button key={filter} className={bboxFilter === filter ? 'tab-button active' : 'tab-button'} onClick={() => setBboxFilter(filter)}>{humanizeStatus(filter)}</button>)}
              <span>{bboxRequirementGroups.length} requirements · {bboxItems.length} claim–screenshot regions</span>
            </div>
            <div className="card bbox-run-context">
              <strong>Displayed prediction source</strong>
              <span>{bboxBundle?.source_run_id ?? 'Legacy audit bundle'}</span>
              {bboxBundle?.source_run_created_at && <span>Source run completed {formatTimestamp(bboxBundle.source_run_created_at)}</span>}
              {bboxBundle?.created_at && <span>Inspection package built {formatTimestamp(bboxBundle.created_at)}</span>}
              <small>Hover over a box to see its claims. Click the box to accept it; use the controls below for incorrect or uncertain regions. High-resolution originals are used for display with deterministically converted coordinates.</small>
            </div>
            <div className="bbox-requirement-list">
              {bboxRequirementGroups.map((group) => (
                <article className="card bbox-requirement-card" key={group.key}>
                  <div className="panel-header">
                    <div><h3>{group.requirementId}</h3><span>{group.flowId} · {group.claims.length} claims</span></div>
                    <div className="review-mini-stack">
                      <span className={`status-pill ${group.requirementId.startsWith('CONTR-') ? 'boundary' : 'neutral'}`}>{group.requirementId.startsWith('CONTR-') ? 'Contrastive audit requirement' : 'Source requirement'}</span>
                      <span>{group.screens.length} screens shown{group.omittedScreens > 0 ? ` · ${group.omittedScreens} repeated screens hidden` : ''}</span>
                    </div>
                  </div>
                  <p className="audit-requirement-text"><strong>Requirement:</strong> {group.requirementText}</p>
                  <div className="bbox-claim-summary">
                    {group.claims.map((claim) => (
                      <div key={claim.claimId}>
                        <strong>{claim.claimId}</strong>
                        {claim.status
                          ? <span className={`status-pill ${statusClass(claim.status)}`}>{humanizeStatus(claim.status)}</span>
                          : <span className="status-pill neutral">Not specified</span>}
                        <span>{claim.text}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bbox-requirement-screens">
                    {group.screens.map((screen) => (
                      <section className="bbox-screen-group" key={`${group.key}-${screen.stepIndex}`}>
                        <div className="panel-header">
                          <div><h4>Step {screen.stepIndex}</h4><span>{screen.item.image_width}×{screen.item.image_height} · {screen.regions.length} distinct regions</span></div>
                          <a className="secondary-button full-resolution-link" href={resolveAssetUrl(screen.item.image_url)} target="_blank" rel="noreferrer">Open full-resolution screenshot</a>
                        </div>
                        <AuditBoundingBoxCanvas
                          item={screen.item}
                          predictions={screen.regions}
                          savingBoxIds={savingBoxIds}
                          onAccept={(items) => void judgeBboxRegion(items, 'VALID')}
                          onIncorrect={(items, category, note) => void judgeBboxRegion(items, 'INCORRECT', category, note)}
                        />
                        <OmniParserCandidatePicker
                          auditId={selectedAuditId}
                          imageItem={screen.item}
                          claimItems={screen.items}
                          savingBoxIds={savingBoxIds}
                          onSelect={(item, candidateId) => void saveCandidateSelection(item, candidateId)}
                        />
                        <div className="bbox-region-list">
                          {screen.items.map((item) => (
                            <div className="bbox-region-review" key={item.audit_item_id}>
                              <div className="bbox-prediction-meta">
                                <strong>{item.claim_id}: {item.prediction ? `“${item.prediction.matched_text}”` : 'No region proposed'}</strong>
                                {item.prediction && <><span>{humanizeStatus(item.prediction.source)} · confidence {item.prediction.score.toFixed(3)}</span><code>{Math.round(item.prediction.bbox.x1)}, {Math.round(item.prediction.bbox.y1)} → {Math.round(item.prediction.bbox.x2)}, {Math.round(item.prediction.bbox.y2)}</code></>}
                              </div>
                              <BoundingBoxInspectionControls item={item} onSave={(status, note) => void saveBboxJudgment(item, status, note)} />
                            </div>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function BoundingBoxInspectionControls({item, onSave}: {
  item: BoundingBoxAuditItem
  onSave: (status: 'VALID' | 'INCORRECT' | 'UNCERTAIN', note: string) => void
}) {
  const [note, setNote] = useState(item.inspection_judgment?.note ?? '')

  useEffect(() => setNote(item.inspection_judgment?.note ?? ''), [item.audit_item_id, item.inspection_judgment?.updated_at])

  return (
    <div className="bbox-inspection-controls">
      <strong>Quick judgment</strong>
      <div className="button-row">
        {(['VALID', 'INCORRECT', 'UNCERTAIN'] as const).map((status) => (
          <button
            key={status}
            className={item.inspection_judgment?.status === status ? `judgment-button active ${status.toLowerCase()}` : 'secondary-button judgment-button'}
            onClick={() => onSave(status, note)}
          >
            {status === 'VALID' ? '✓ Valid' : status === 'INCORRECT' ? '✕ Incorrect' : '? Unsure'}
          </button>
        ))}
      </div>
      <label>Optional note<textarea rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder="For example: box highlights the title, but the supporting dietary links are in the left navigation." /></label>
      {item.inspection_judgment && <small>Saved as {humanizeStatus(item.inspection_judgment.status)}</small>}
    </div>
  )
}

function AuditBoundingBoxCanvas({item, predictions, savingBoxIds, onAccept, onIncorrect}: {
  item: BoundingBoxAuditItem
  predictions: Array<{bbox: BoundingBox; label: string; items: BoundingBoxAuditItem[]}>
  savingBoxIds: Set<string>
  onAccept: (items: BoundingBoxAuditItem[]) => void
  onIncorrect: (items: BoundingBoxAuditItem[], category: 'MISALIGNED' | 'WRONG_LOCATION' | 'SEMANTIC_ERROR', note: string) => void
}) {
  const [openPredictionKey, setOpenPredictionKey] = useState<string | null>(null)
  const [overlaysHidden, setOverlaysHidden] = useState(false)
  const [notes, setNotes] = useState<Record<string, string>>({})
  const closeTimer = useRef<number | null>(null)

  const orderedPredictions = useMemo(() => predictions
    .map((prediction, sourceIndex) => ({
      ...prediction,
      sourceIndex,
      area: Math.max(0, prediction.bbox.x2 - prediction.bbox.x1) * Math.max(0, prediction.bbox.y2 - prediction.bbox.y1),
    }))
    .sort((left, right) => right.area - left.area || left.sourceIndex - right.sourceIndex), [predictions])

  const overlappingPredictions = useMemo(() => orderedPredictions
    .filter((candidate, candidateIndex) => orderedPredictions.some((other, otherIndex) => {
      if (candidateIndex === otherIndex) return false
      return candidate.bbox.x1 < other.bbox.x2
        && candidate.bbox.x2 > other.bbox.x1
        && candidate.bbox.y1 < other.bbox.y2
        && candidate.bbox.y2 > other.bbox.y1
    }))
    .sort((left, right) => left.area - right.area || left.sourceIndex - right.sourceIndex), [orderedPredictions])

  function cancelClose() {
    if (closeTimer.current !== null) {
      window.clearTimeout(closeTimer.current)
      closeTimer.current = null
    }
  }

  function openPopover(key: string) {
    cancelClose()
    setOpenPredictionKey(key)
  }

  function scheduleClose() {
    cancelClose()
    closeTimer.current = window.setTimeout(() => setOpenPredictionKey(null), 300)
  }

  useEffect(() => () => cancelClose(), [])

  const overlayStyle = (box: BoundingBox) => ({
    left: `${(box.x1 / item.image_width) * 100}%`, top: `${(box.y1 / item.image_height) * 100}%`,
    width: `${((box.x2 - box.x1) / item.image_width) * 100}%`, height: `${((box.y2 - box.y1) / item.image_height) * 100}%`,
  })

  return (
    <div className="audit-bbox-stack">
      <div className="bbox-canvas-display-controls">
        <button type="button" onClick={() => setOverlaysHidden((hidden) => !hidden)}>
          {overlaysHidden ? 'Show bounding boxes' : 'Hide bounding boxes'}
        </button>
        <span>Box labels appear on hover or selection.</span>
      </div>
      {overlappingPredictions.length > 0 && (
        <div className="bbox-overlap-picker" aria-label="Overlapping bounding-box selector">
          <strong>Overlapping regions</strong>
          <span>Smallest regions are in front. Select a label here if the desired box is still covered.</span>
          <div>
            {overlappingPredictions.map((prediction) => {
              const predictionKey = `${prediction.label}-${prediction.sourceIndex}`
              return (
                <button
                  type="button"
                  key={predictionKey}
                  className={openPredictionKey === predictionKey ? 'active' : ''}
                  aria-pressed={openPredictionKey === predictionKey}
                  title={`${prediction.label}: ${Math.round(prediction.bbox.x1)}, ${Math.round(prediction.bbox.y1)} → ${Math.round(prediction.bbox.x2)}, ${Math.round(prediction.bbox.y2)}`}
                  onClick={() => {
                    cancelClose()
                    setOpenPredictionKey((current) => current === predictionKey ? null : predictionKey)
                  }}
                >
                  {prediction.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
      <div className="audit-bbox-canvas">
        <img src={resolveAssetUrl(item.image_url)} alt={`Evidence step ${item.step_index}`} draggable={false} />
        {!overlaysHidden && orderedPredictions.map((prediction) => {
        const predictionKey = `${prediction.label}-${prediction.sourceIndex}`
        const accepted = prediction.items.every((candidate) => candidate.inspection_judgment?.status === 'VALID')
        const incorrect = prediction.items.every((candidate) => candidate.inspection_judgment?.status === 'INCORRECT')
        const saving = prediction.items.some((candidate) => savingBoxIds.has(candidate.audit_item_id))
        const displayedClaims = [...new Map(
          prediction.items.map((candidate) => [candidate.claim_id, candidate] as const),
        ).values()]
        const claimSummary = displayedClaims.map((candidate) => `${candidate.claim_id}: ${candidate.claim_text}`).join('\n')
        const savedCategory = prediction.items.find((candidate) => candidate.inspection_judgment?.error_category)?.inspection_judgment?.error_category
        const note = notes[predictionKey] ?? prediction.items.find((candidate) => candidate.inspection_judgment?.note)?.inspection_judgment?.note ?? ''
        return (
          <div
            key={predictionKey}
            className={`audit-box prediction clickable${accepted ? ' accepted' : ''}${incorrect ? ' incorrect' : ''}${saving ? ' saving' : ''}${openPredictionKey === predictionKey ? ' popover-open' : ''}`}
            style={overlayStyle(prediction.bbox)}
            role="button"
            tabIndex={0}
            aria-label={`${accepted ? 'Accepted' : 'Accept'} bounding box for ${claimSummary}`}
            onMouseEnter={() => openPopover(predictionKey)}
            onMouseLeave={scheduleClose}
            onFocus={() => openPopover(predictionKey)}
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) scheduleClose()
            }}
            onClick={() => {
              if (!incorrect) onAccept(prediction.items)
              openPopover(predictionKey)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                if (!incorrect) onAccept(prediction.items)
              }
            }}
          >
            <span>{saving ? 'Saving…' : accepted ? `✓ ${prediction.label}` : incorrect ? `✕ ${prediction.label}` : prediction.label}</span>
            <div
              className="audit-box-tooltip"
              onMouseEnter={cancelClose}
              onMouseLeave={scheduleClose}
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            >
              {displayedClaims.map((candidate) => (
                <div key={candidate.claim_id}>
                  <strong>{candidate.claim_id}</strong>
                  <span>{candidate.claim_text}</span>
                </div>
              ))}
              <label className="bbox-hover-note">
                Optional note
                <textarea
                  rows={2}
                  value={note}
                  placeholder="What is wrong with this region?"
                  onChange={(event) => setNotes((current) => ({...current, [predictionKey]: event.target.value}))}
                />
              </label>
              <div className="audit-box-tooltip-actions">
                <button
                  type="button"
                  className="bbox-hover-action accept"
                  onClick={(event) => {
                    event.stopPropagation()
                    onAccept(prediction.items)
                  }}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  ✓ Accept
                </button>
                <button
                  type="button"
                  className={`bbox-hover-action incorrect${savedCategory === 'MISALIGNED' ? ' active' : ''}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    onIncorrect(prediction.items, 'MISALIGNED', note)
                  }}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  Misaligned
                </button>
                <button
                  type="button"
                  className={`bbox-hover-action incorrect${savedCategory === 'WRONG_LOCATION' ? ' active' : ''}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    onIncorrect(prediction.items, 'WRONG_LOCATION', note)
                  }}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  Wrong location
                </button>
                <button
                  type="button"
                  className={`bbox-hover-action incorrect${savedCategory === 'SEMANTIC_ERROR' ? ' active' : ''}`}
                  onClick={(event) => {
                    event.stopPropagation()
                    onIncorrect(prediction.items, 'SEMANTIC_ERROR', note)
                  }}
                  onKeyDown={(event) => event.stopPropagation()}
                >
                  Semantic error
                </button>
              </div>
              <small>
                {saving
                  ? 'Saving judgment…'
                  : accepted
                    ? 'Saved as accepted'
                    : incorrect
                      ? `Saved as ${humanizeStatus(savedCategory ?? 'INCORRECT')}`
                      : 'Click the box or choose Accept'}
              </small>
            </div>
          </div>
        )
        })}
      </div>
    </div>
  )
}

function OmniParserCandidatePicker({auditId, imageItem, claimItems, savingBoxIds, onSelect}: {
  auditId: string
  imageItem: BoundingBoxAuditItem
  claimItems: BoundingBoxAuditItem[]
  savingBoxIds: Set<string>
  onSelect: (item: BoundingBoxAuditItem, candidateId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [bundle, setBundle] = useState<OmniParserCandidateBundle | null>(null)
  const [bundleItemId, setBundleItemId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sourceFilter, setSourceFilter] = useState<'top5' | 'omniparser_ui' | 'tesseract_line' | 'all'>('top5')
  const [selectedItemId, setSelectedItemId] = useState(claimItems[0]?.audit_item_id ?? '')

  if (!imageItem.flow_id.startsWith('02_gamestop_')) return null

  const selectedItem = claimItems.find((item) => item.audit_item_id === selectedItemId) ?? claimItems[0]
  const shownCandidates = sourceFilter === 'top5'
    ? (bundle?.candidates ?? []).slice(0, 5)
    : (bundle?.candidates ?? []).filter((candidate) => sourceFilter === 'all' || candidate.source === sourceFilter)

  const overlayStyle = (box: BoundingBox) => ({
    left: `${(box.x1 / imageItem.image_width) * 100}%`,
    top: `${(box.y1 / imageItem.image_height) * 100}%`,
    width: `${((box.x2 - box.x1) / imageItem.image_width) * 100}%`,
    height: `${((box.y2 - box.y1) / imageItem.image_height) * 100}%`,
  })

  async function loadBundle(itemId: string) {
    if (!itemId || (bundle && bundleItemId === itemId) || loading) return
    setLoading(true)
    setError('')
    setBundle(null)
    try {
      setBundle(await api.getOmniParserCandidates(auditId, itemId))
      setBundleItemId(itemId)
    } catch (candidateError) {
      setError(candidateError instanceof Error ? candidateError.message : 'Failed to load local candidates')
    } finally {
      setLoading(false)
    }
  }

  async function toggle() {
    const nextExpanded = !expanded
    setExpanded(nextExpanded)
    if (!nextExpanded || !selectedItem) return
    await loadBundle(selectedItem.audit_item_id)
  }

  return (
    <section className="omniparser-picker">
      <button type="button" className="secondary-button" onClick={() => void toggle()}>
        {expanded ? 'Hide local OmniParser candidates' : 'Try local OmniParser candidates'}
      </button>
      {expanded && (
        <div className="omniparser-picker-body">
          <div className="omniparser-picker-copy">
            <strong>Local claim-specific region ranking</strong>
            <span>Florence captions and OCR are ranked against the selected claim. Only the five best clean-image candidates are shown initially; selections remain separate from the pipeline prediction.</span>
          </div>
          <div className="omniparser-picker-controls">
            <label>
              Pick a region for
              <select value={selectedItem?.audit_item_id ?? ''} onChange={(event) => {
                const itemId = event.target.value
                setSelectedItemId(itemId)
                void loadBundle(itemId)
              }}>
                {claimItems.map((item) => <option key={item.audit_item_id} value={item.audit_item_id}>{item.claim_id}: {item.claim_text}</option>)}
              </select>
            </label>
            <div className="button-row">
              {([
                ['top5', 'Ranked top 5'],
                ['omniparser_ui', 'UI regions'],
                ['tesseract_line', 'OCR text lines'],
                ['all', 'All'],
              ] as const).map(([value, label]) => (
                <button key={value} type="button" className={sourceFilter === value ? 'tab-button active' : 'tab-button'} onClick={() => setSourceFilter(value)}>{label}</button>
              ))}
            </div>
          </div>
          {loading && <span>Loading local candidates…</span>}
          {error && <span className="helper-text">{error}</span>}
          {bundle && selectedItem && (
            <>
              <div className="audit-bbox-canvas omniparser-candidate-canvas">
                <img src={resolveAssetUrl(imageItem.image_url)} alt={`OmniParser candidates for step ${imageItem.step_index}`} draggable={false} />
                {shownCandidates.map((candidate) => {
                  const selected = selectedItem.candidate_selection?.candidate_id === candidate.candidate_id
                  const saving = savingBoxIds.has(selectedItem.audit_item_id)
                  return (
                    <button
                      type="button"
                      key={candidate.candidate_id}
                      className={`omniparser-candidate ${candidate.source === 'tesseract_line' ? 'text' : 'ui'}${selected ? ' selected' : ''}`}
                      style={overlayStyle(candidate.bbox)}
                      title={`${candidate.candidate_id} · rank ${candidate.rank ?? '?'} · score ${(candidate.rank_score ?? 0).toFixed(3)}${candidate.caption ? ` · ${candidate.caption}` : ''}${candidate.text ? ` · OCR: ${candidate.text}` : ''}`}
                      aria-label={`Use ranked candidate ${candidate.candidate_id} for ${selectedItem.claim_id}`}
                      disabled={saving}
                      onClick={() => onSelect(selectedItem, candidate.candidate_id)}
                    >
                      <span>{selected ? '✓ ' : ''}#{candidate.rank ?? '?'} {candidate.candidate_id}</span>
                    </button>
                  )
                })}
              </div>
              <div className="omniparser-selection-summary">
                <span>{shownCandidates.length} candidates shown · {bundle.ranking_method ?? 'local ranking'}</span>
                {selectedItem.candidate_selection
                  ? <strong>Saved for {selectedItem.claim_id}: {selectedItem.candidate_selection.candidate_id}{selectedItem.candidate_selection.text ? ` — ${selectedItem.candidate_selection.text}` : ''}</strong>
                  : <span>No local replacement selected for {selectedItem.claim_id}.</span>}
              </div>
              {sourceFilter === 'top5' && (
                <ol className="omniparser-ranked-list">
                  {shownCandidates.map((candidate) => (
                    <li key={`rank-${candidate.candidate_id}`}>
                      <button type="button" disabled={savingBoxIds.has(selectedItem.audit_item_id)} onClick={() => onSelect(selectedItem, candidate.candidate_id)}>
                        <strong>#{candidate.rank} {candidate.candidate_id}</strong>
                        <span>{candidate.caption || candidate.text || candidate.associated_text || 'No semantic description available'}</span>
                        <small>score {(candidate.rank_score ?? 0).toFixed(3)}</small>
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}

function UploadVerificationPage({
  onBack,
  onProjectCreated,
}: {
  onBack: () => void
  onProjectCreated: (flowId: string) => void
}) {
  const [projectName, setProjectName] = useState('')
  const [description, setDescription] = useState('')
  const [requirementsContent, setRequirementsContent] = useState('')
  const [requirementsFilename, setRequirementsFilename] = useState<string | undefined>()
  const [screenshots, setScreenshots] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [creating, setCreating] = useState(false)
  const [loadingProject, setLoadingProject] = useState(false)
  const [message, setMessage] = useState('')
  const [project, setProject] = useState<CreateUploadedFlowResponse | null>(null)
  const [pipelineRun, setPipelineRun] = useState<PipelineVerificationRun | null>(null)

  useEffect(() => {
    const flowId = new URLSearchParams(window.location.search).get('flow_id')
    if (!flowId) {
      return
    }
    let cancelled = false
    setLoadingProject(true)
    Promise.all([api.getFlow(flowId), api.getSteps(flowId), api.getLatestPipelineVerification(flowId).catch(() => null)])
      .then(([flow, steps, latestRun]) => {
        if (cancelled) {
          return
        }
        setProject({
          flow,
          steps,
          requirements: [],
          requirements_count: Number(flow.task?.requirements_count ?? 0),
        })
        setPipelineRun(latestRun)
      })
      .catch((error) => {
        if (!cancelled) {
          setMessage(error instanceof Error ? error.message : 'Failed to load the uploaded project')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingProject(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  function addScreenshots(files: File[]) {
    const imageFiles = files.filter((file) => file.type.startsWith('image/'))
    if (imageFiles.length !== files.length) {
      setMessage('Only image files were added. Unsupported files were skipped.')
    } else {
      setMessage('')
    }
    setScreenshots((current) => [...current, ...imageFiles].slice(0, 20))
  }

  function moveScreenshot(index: number, direction: -1 | 1) {
    const nextIndex = index + direction
    if (nextIndex < 0 || nextIndex >= screenshots.length) {
      return
    }
    setScreenshots((current) => {
      const next = [...current]
      const [file] = next.splice(index, 1)
      next.splice(nextIndex, 0, file)
      return next
    })
  }

  async function handleRequirementsFile(file: File | undefined) {
    if (!file) {
      return
    }
    try {
      const content = await file.text()
      setRequirementsContent(content)
      setRequirementsFilename(file.name)
      setMessage('')
    } catch {
      setMessage('Could not read the requirements file.')
    }
  }

  async function createProject() {
    setMessage('')
    if (!projectName.trim() || screenshots.length === 0 || !requirementsContent.trim()) {
      setMessage('Add a project name, at least one screenshot, and at least one requirement.')
      return
    }
    setCreating(true)
    try {
      const encodedScreenshots = await Promise.all(
        screenshots.map(async (file) => ({
          filename: file.name,
          content_base64: await fileToBase64(file),
        })),
      )
      const created = await api.createUploadedFlow({
        project_name: projectName.trim(),
        description: description.trim() || undefined,
        requirements_content: requirementsContent,
        requirements_filename: requirementsFilename,
        screenshots: encodedScreenshots,
      })
      setProject(created)
      setPipelineRun(null)
      onProjectCreated(created.flow.flow_id)
      setMessage(`Project ready with ${created.steps.length} screenshots and ${created.requirements_count} requirements.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to create the verification project')
    } finally {
      setCreating(false)
    }
  }

  function startAnotherProject() {
    setProject(null)
    setPipelineRun(null)
    setProjectName('')
    setDescription('')
    setRequirementsContent('')
    setRequirementsFilename(undefined)
    setScreenshots([])
    setMessage('')
    window.history.pushState({}, '', '/verify/new')
  }

  const currentStep = project ? 3 : screenshots.length > 0 || requirementsContent ? 2 : 1

  return (
    <div className="upload-page">
      <header className="upload-nav">
        <button className="brand-button" onClick={onBack} aria-label="Back to annotation workbench">
          <span className="brand-mark">UV</span>
          <span><strong>UI Verifier</strong><small>Verification studio</small></span>
        </button>
        <div className="button-row">
          {project && <button className="secondary-button" onClick={startAnotherProject}>New project</button>}
          <button className="secondary-button" onClick={onBack}>Back to workbench</button>
        </div>
      </header>

      <main className="upload-main">
        <section className="upload-hero">
          <div>
            <span className="eyebrow">Ad-hoc verification</span>
            <h1>Turn screenshots into inspectable evidence.</h1>
            <p>Upload an ordered UI flow, add requirements, and run the evidence-first pipeline. Every result stays connected to its source screen, including localized bounding boxes when available.</p>
          </div>
          <div className="bbox-feature-card">
            <span className="bbox-feature-icon"><span /></span>
            <div><strong>Bounding boxes included</strong><span>Localized regions are overlaid at the correct image scale.</span></div>
          </div>
        </section>

        <ol className="upload-progress" aria-label="Verification setup progress">
          {['Add inputs', 'Review setup', 'Run & inspect'].map((label, index) => {
            const step = index + 1
            return <li key={label} className={currentStep >= step ? 'active' : ''}><span>{currentStep > step ? '✓' : step}</span>{label}</li>
          })}
        </ol>

        {message && <section className="upload-message">{message}</section>}
        {loadingProject && <section className="upload-card">Loading uploaded project…</section>}

        {!project && !loadingProject && (
          <section className="upload-form-grid">
            <div className="upload-card upload-card-wide">
              <div className="upload-section-heading">
                <span className="section-number">1</span>
                <div><h2>Project details</h2><p>Give this verification run a recognizable name.</p></div>
              </div>
              <div className="project-fields">
                <label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Checkout confirmation flow" /></label>
                <label>Context <span className="optional-label">Optional</span><input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What should this UI flow demonstrate?" /></label>
              </div>
            </div>

            <div className="upload-card">
              <div className="upload-section-heading">
                <span className="section-number">2</span>
                <div><h2>Screenshots</h2><p>Order them as the user experiences the flow.</p></div>
              </div>
              <label
                className={dragActive ? 'drop-zone active' : 'drop-zone'}
                onDragEnter={(event) => { event.preventDefault(); setDragActive(true) }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setDragActive(false)}
                onDrop={(event) => {
                  event.preventDefault()
                  setDragActive(false)
                  addScreenshots(Array.from(event.dataTransfer.files))
                }}
              >
                <input type="file" accept="image/*" multiple onChange={(event) => addScreenshots(Array.from(event.target.files ?? []))} />
                <span className="drop-icon">↑</span>
                <strong>Drop screenshots here</strong>
                <span>or click to browse · PNG, JPG, WebP · up to 20</span>
              </label>
              {screenshots.length > 0 && (
                <div className="upload-thumbnail-list">
                  {screenshots.map((file, index) => (
                    <UploadThumbnail
                      key={`${file.name}-${file.lastModified}-${index}`}
                      file={file}
                      index={index}
                      count={screenshots.length}
                      onMove={moveScreenshot}
                      onRemove={() => setScreenshots((current) => current.filter((_, fileIndex) => fileIndex !== index))}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="upload-card">
              <div className="upload-section-heading">
                <span className="section-number">3</span>
                <div><h2>Requirements</h2><p>One per line, or upload JSON, TXT, or Markdown.</p></div>
              </div>
              <textarea
                className="requirements-input"
                value={requirementsContent}
                onChange={(event) => { setRequirementsContent(event.target.value); setRequirementsFilename(undefined) }}
                rows={10}
                placeholder={'The confirmation page shall show the order number.\nThe user shall be able to return to the store.'}
              />
              <label className="requirements-file-button">
                <input type="file" accept=".json,.txt,.md,application/json,text/plain,text/markdown" onChange={(event) => void handleRequirementsFile(event.target.files?.[0])} />
                <span>Attach requirements file</span>
                <strong>{requirementsFilename ?? 'No file selected'}</strong>
              </label>
              <p className="format-hint">JSON may be a list of strings or objects with <code>text</code> and optional metadata.</p>
            </div>

            <div className="upload-submit-card upload-card-wide">
              <div><strong>Ready to create your verification workspace?</strong><span>Inputs stay local under this repository.</span></div>
              <button onClick={() => void createProject()} disabled={creating}>{creating ? 'Preparing workspace…' : 'Create project & continue →'}</button>
            </div>
          </section>
        )}

        {project && (
          <section className="uploaded-workspace">
            <section className="upload-card workspace-summary">
              <div>
                <span className="eyebrow">Project ready</span>
                <h2>{project.flow.website ?? project.flow.flow_id}</h2>
                <p>{project.flow.confirmed_task}</p>
              </div>
              <div className="workspace-stats">
                <Metric label="Screenshots" value={String(project.steps.length)} />
                <Metric label="Requirements" value={String(project.requirements_count)} />
                <Metric label="Evidence regions" value="Enabled" />
              </div>
            </section>

            <section className="upload-card">
              <div className="panel-header"><h3>Uploaded flow</h3><span>Step order used by the pipeline</span></div>
              <div className="uploaded-step-strip">
                {project.steps.map((step) => (
                  <figure key={step.step_index} id={`uploaded-step-${step.step_index}`}>
                    <img src={resolveAssetUrl(step.image_url)} alt={`Uploaded step ${step.step_index}`} />
                    <figcaption>Step {step.step_index}</figcaption>
                  </figure>
                ))}
              </div>
            </section>

            <VerificationRunPanel
              key={project.flow.flow_id}
              flowId={project.flow.flow_id}
              steps={project.steps}
              pipelineRun={pipelineRun}
              verificationGold={[]}
              defaultRequirementsSource="uploaded"
              onJumpToStep={(stepIndex) => document.getElementById(`uploaded-step-${stepIndex}`)?.scrollIntoView({behavior: 'smooth', block: 'center'})}
              onEditVerificationGold={() => undefined}
              onAcceptVerificationGold={async () => undefined}
            />
          </section>
        )}
      </main>
    </div>
  )
}

function UploadThumbnail({
  file,
  index,
  count,
  onMove,
  onRemove,
}: {
  file: File
  index: number
  count: number
  onMove: (index: number, direction: -1 | 1) => void
  onRemove: () => void
}) {
  const [previewUrl, setPreviewUrl] = useState('')
  useEffect(() => {
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  return (
    <div className="upload-thumbnail">
      <span className="thumbnail-order">{index + 1}</span>
      {previewUrl && <img src={previewUrl} alt={`Screenshot ${index + 1}: ${file.name}`} />}
      <div><strong title={file.name}>{file.name}</strong><span>{formatFileSize(file.size)}</span></div>
      <div className="thumbnail-actions">
        <button type="button" className="secondary-button" onClick={() => onMove(index, -1)} disabled={index === 0} aria-label="Move screenshot earlier">←</button>
        <button type="button" className="secondary-button" onClick={() => onMove(index, 1)} disabled={index === count - 1} aria-label="Move screenshot later">→</button>
        <button type="button" className="secondary-button remove" onClick={onRemove} aria-label="Remove screenshot">×</button>
      </div>
    </div>
  )
}


function OverviewPanel({
  steps,
  activeCandidates,
  gold,
  onJumpToStep,
  onOpenZoom,
  onPromote,
  onEditCandidate,
  onReject,
  onEditGold,
  onDeleteGold,
  onRegenerateExpectedClaims,
  regeneratingClaims,
}: {
  steps: FlowStep[]
  activeCandidates: Requirement[]
  gold: VerificationGoldItem[]
  onJumpToStep: (stepIndex: number) => void
  onOpenZoom: (step: FlowStep) => void
  onPromote: (requirement: Requirement) => void
  onEditCandidate: (requirement: Requirement) => void
  onReject: (requirement: Requirement) => void
  onEditGold: (requirement: VerificationGoldItem) => void
  onDeleteGold: (requirement: VerificationGoldItem) => void
  onRegenerateExpectedClaims: () => void
  regeneratingClaims: boolean
}) {
  return (
    <section className="content-grid">
      <section className="card panel-wide">
        <div className="panel-header">
          <h3>Screenshots overview</h3>
          <span>{steps.length} images</span>
        </div>
        <div className="step-grid overview-step-grid">
          {steps.map((step) => (
            <article key={step.step_index} id={`step-${step.step_index}`} className="step-card compact-step-card">
              <div className="step-label">Step {step.step_index}</div>
              {step.artifact_label && <div className="artifact-badge">{step.artifact_label}{step.artifact_page ? ` · page ${step.artifact_page}` : ''}</div>}
              <img src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`} loading="lazy" onClick={() => onOpenZoom(step)} />
              <button className="step-link-button" onClick={() => onJumpToStep(step.step_index)}>
                Jump to screen
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Pending candidate requirements</h3>
          <span>{activeCandidates.length}</span>
        </div>
        <div className="requirement-list compact-list">
          {activeCandidates.map((requirement) => (
            <RequirementCard
              key={requirement.requirement_id}
              requirement={requirement}
              onJumpToStep={onJumpToStep}
              actions={
                <div className="button-row left wrap">
                  <button onClick={() => onPromote(requirement)}>Promote to gold</button>
                  <button className="secondary-button" onClick={() => onEditCandidate(requirement)}>
                    Edit / review
                  </button>
                  <button className="danger-button" onClick={() => onReject(requirement)}>
                    Reject
                  </button>
                </div>
              }
            />
          ))}
        </div>
      </section>

      <section className="card">
        <div className="panel-header">
          <div>
            <h3>Verification benchmark items</h3>
            <span>{gold.length}</span>
          </div>
          <button className="secondary-button" onClick={onRegenerateExpectedClaims} disabled={gold.length === 0 || regeneratingClaims}>
            {regeneratingClaims ? 'Regenerating claims...' : 'Regenerate expected claims'}
          </button>
        </div>
        <div className="requirement-list compact-list">
          {gold.map((requirement) => (
            <RequirementCard
              key={requirement.requirement_id}
              requirement={requirement}
              onJumpToStep={onJumpToStep}
              actions={
                <div className="button-row left wrap">
                  <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                    Edit verification labels
                  </button>
                  <button className="danger-button" onClick={() => onDeleteGold(requirement)}>
                    Delete requirement
                  </button>
                </div>
              }
            />
          ))}
        </div>
      </section>
    </section>
  )
}


function VerificationRunPanel({
  flowId,
  steps,
  pipelineRun,
  verificationGold,
  defaultRequirementsSource = 'benchmark',
  onJumpToStep,
  onEditVerificationGold,
  onAcceptVerificationGold,
}: {
  flowId: string
  steps: FlowStep[]
  pipelineRun: PipelineVerificationRun | null
  verificationGold: VerificationGoldItem[]
  defaultRequirementsSource?: StartPipelineRunPayload['requirements_source']
  onJumpToStep: (stepIndex: number) => void
  onEditVerificationGold: (requirement: VerificationGoldItem) => void
  onAcceptVerificationGold: (requirement: VerificationGoldItem) => Promise<void>
}) {
  const [selectedRequirementId, setSelectedRequirementId] = useState<string | null>(null)
  const [runs, setRuns] = useState<PipelineRunSummary[]>([])
  const [runsState, setRunsState] = useState<LoadState>('idle')
  const [selectedRunId, setSelectedRunId] = useState<string>('')
  const [selectedRun, setSelectedRun] = useState<PipelineVerificationRun | null>(pipelineRun)
  const [runJob, setRunJob] = useState<PipelineRunJob | null>(null)
  const [runMessage, setRunMessage] = useState<string>('')
  const [acceptingRequirementId, setAcceptingRequirementId] = useState<string | null>(null)
  const [reviewCategoryId, setReviewCategoryId] = useState<ReviewCategoryId>('all')
  const [runForm, setRunForm] = useState<StartPipelineRunPayload>({
    verifier: 'gemini-image',
    verifier_model: 'gemini-3.1-flash-lite',
    retriever: 'lexical',
    retriever_provider: 'deepseek',
    retriever_model: 'deepseek-chat',
    requirements_source: defaultRequirementsSource,
    top_k: 3,
    llm_claim_fallback: false,
    claim_provider: 'deepseek',
    claim_model: 'deepseek-chat',
    max_claims: 4,
    max_images: 6,
    max_gemini_api_calls: 10,
    gemini_max_retries: 2,
    use_cache: true,
    output_dir_name: 'ui_verification_runs',
  })
  const goldById = useMemo(() => new Map(verificationGold.map((item) => [item.requirement_id, item])), [verificationGold])
  const activeRun = selectedRun ?? pipelineRun
  const resultById = useMemo(() => new Map((activeRun?.results ?? []).map((result) => [result.requirement_id, result])), [activeRun])
  const selectedResult = selectedRequirementId ? resultById.get(selectedRequirementId) ?? null : null
  const selectedGold = selectedRequirementId ? goldById.get(selectedRequirementId) ?? null : null

  useEffect(() => {
    setSelectedRun(pipelineRun)
  }, [pipelineRun])

  useEffect(() => {
    setRunForm((current) => ({...current, requirements_source: defaultRequirementsSource}))
  }, [flowId, defaultRequirementsSource])

  useEffect(() => {
    void refreshRuns()
  }, [flowId])

  useEffect(() => {
    if (!runJob || (runJob.status !== 'running' && runJob.status !== 'not_started')) {
      return
    }
    const interval = window.setInterval(async () => {
      try {
        const latest = await api.getPipelineVerificationJob(runJob.job_id)
        setRunJob(latest)
        if (latest.status === 'completed') {
          await refreshRuns()
          if (latest.output_path) {
            const list = await api.listPipelineVerificationRuns(flowId)
            const completedRun = list.runs.find((run) => run.path === latest.output_path)
            if (completedRun) {
              await selectRun(completedRun.run_id)
            }
          }
        }
      } catch (error) {
        setRunMessage(error instanceof Error ? error.message : 'Failed to refresh run status')
      }
    }, 2000)
    return () => window.clearInterval(interval)
  }, [runJob?.job_id, runJob?.status, flowId])

  async function refreshRuns() {
    setRunsState('loading')
    setRunMessage('')
    try {
      const response = await api.listPipelineVerificationRuns(flowId)
      const orderedRuns = orderPipelineRunsForDisplay(response.runs)
      setRuns(orderedRuns)
      setRunsState('idle')
      if (orderedRuns.length > 0) {
        const nextRunId = orderedRuns[0].run_id
        setSelectedRunId(nextRunId)
        await selectRun(nextRunId)
      } else {
        setSelectedRunId('')
        setSelectedRun(null)
      }
    } catch (error) {
      setRunsState('error')
      setRunMessage(error instanceof Error ? error.message : 'Failed to load verification runs')
    }
  }

  async function selectRun(runId: string) {
    setSelectedRunId(runId)
    setSelectedRequirementId(null)
    const run = await api.getPipelineVerificationRun(flowId, runId)
    setSelectedRun(run)
  }

  async function startRun() {
    setRunMessage('')
    if (runForm.verifier === 'gemini-image' && runForm.max_gemini_api_calls === 0) {
      setRunMessage('Gemini image runs require max Gemini API calls greater than 0 or -1.')
      return
    }
    try {
      const job = await api.startPipelineVerificationRun(flowId, runForm)
      setRunJob(job)
      setRunMessage(`Started pipeline job ${job.job_id}.`)
    } catch (error) {
      setRunMessage(error instanceof Error ? error.message : 'Failed to start pipeline run')
    }
  }

  function selectVerifier(verifier: StartPipelineRunPayload['verifier']) {
    setRunForm((current) => ({
      ...current,
      verifier,
      max_gemini_api_calls: verifier === 'gemini-image' && current.max_gemini_api_calls === 0
        ? 10
        : current.max_gemini_api_calls,
    }))
  }

  async function acceptBenchmarkItem(requirement: VerificationGoldItem) {
    setRunMessage('')
    setAcceptingRequirementId(requirement.requirement_id)
    try {
      await onAcceptVerificationGold(requirement)
      setRunMessage(`${requirement.requirement_id} accepted.`)
    } catch (error) {
      setRunMessage(error instanceof Error ? error.message : 'Failed to accept verification benchmark item')
    } finally {
      setAcceptingRequirementId(null)
    }
  }

  const requirementsPath = runForm.requirements_source === 'benchmark'
    ? `data/annotations/verification_gold/${flowId}/verification_gold.json`
    : runForm.requirements_source === 'uploaded'
      ? `data/generated/uploaded_flows/${flowId}/requirements.json`
      : `data/annotations/requirements_gold/${flowId}/gold_requirements.json`
  const flowPath = runForm.requirements_source === 'uploaded'
    ? `data/processed/flows/uploads/${flowId}`
    : `data/processed/flows/mind2web/${flowId}`
  const cliRequirementsSource = runForm.requirements_source === 'uploaded' ? 'custom' : runForm.requirements_source
  const usesGeminiVerifier = runForm.verifier === 'gemini-image'
  const cliGeminiOptions = usesGeminiVerifier
    ? ` --verifier-model ${runForm.verifier_model} --max-verifier-images ${runForm.max_images} --max-gemini-api-calls ${runForm.max_gemini_api_calls} --gemini-max-retries ${runForm.gemini_max_retries}`
    : ''
  const cliRetrieverOptions = runForm.retriever === 'llm'
    ? ` --retriever-provider ${runForm.retriever_provider} --retriever-model ${runForm.retriever_model}`
    : ''
  const cliClaimOptions = runForm.llm_claim_fallback
    ? ` --llm-claim-fallback --claim-provider ${runForm.claim_provider} --claim-model ${runForm.claim_model}`
    : ' --no-llm-claim-fallback'
  const cliCommand = `PYTHONPATH=src:. python scripts/run_verification_pipeline.py --flow-dir ${flowPath} --requirements ${requirementsPath} --requirements-source ${cliRequirementsSource} --out data/generated/${runForm.output_dir_name}/${flowId}.json --retriever ${runForm.retriever}${cliRetrieverOptions} --top-k ${runForm.top_k} --max-claims ${runForm.max_claims}${cliClaimOptions} --verifier ${usesGeminiVerifier ? 'gemini-image' : 'deterministic'}${cliGeminiOptions}`

  const metadata = activeRun?.metadata ?? {}
  const geminiDiagnostics = metadata.gemini_image_verifier && typeof metadata.gemini_image_verifier === 'object'
    ? metadata.gemini_image_verifier as Record<string, unknown>
    : null
  const geminiApiCalls = Number(geminiDiagnostics?.api_calls ?? 0)
  const geminiCacheHits = Number(geminiDiagnostics?.cache_hits ?? 0)
  const verifierFallbacks = Number(geminiDiagnostics?.fallbacks ?? 0)
  const verifierFailures = Array.isArray(geminiDiagnostics?.failures)
    ? geminiDiagnostics.failures.filter((failure): failure is Record<string, unknown> => Boolean(failure) && typeof failure === 'object')
    : []
  const allGeminiVerificationFailed = metadata.verifier === 'gemini-image'
    && Boolean(geminiDiagnostics)
    && geminiApiCalls + geminiCacheHits === 0
    && verifierFallbacks > 0
  const selectedRunSummary = runs.find((run) => run.run_id === selectedRunId) ?? runs[0] ?? null
  const labelDistribution = (metadata.label_distribution ?? labelDistributionForResults(activeRun?.results ?? [])) as Record<string, number>
  const claimStatusDistribution = (metadata.claim_status_distribution ?? claimStatusDistributionForResults(activeRun?.results ?? [])) as Record<string, number>
  const comparisonRows = useMemo(() => {
    return (activeRun?.results ?? []).map((result) => {
      const goldItem = goldById.get(result.requirement_id)
      const referenceLabel = goldItem?.verification_label ?? null
      const matchesReference = referenceLabel ? normalizeDisplayValue(referenceLabel) === normalizeDisplayValue(result.final_label) : null
      const predictedEvidenceSteps = uniqueEvidenceSteps(result.evidence)
      const referenceEvidenceSteps = goldItem?.evidence_steps ?? []
      const evidenceOverlap = intersectNumbers(referenceEvidenceSteps, predictedEvidenceSteps)
      const categoryIds = reviewCategoriesForComparison(goldItem ?? null, result, evidenceOverlap)
      return {
        requirement_id: result.requirement_id,
        predicted_label: result.final_label,
        reference_label: referenceLabel,
        matches_reference: matchesReference,
        predicted_evidence_steps: predictedEvidenceSteps,
        reference_evidence_steps: referenceEvidenceSteps,
        evidence_overlap: evidenceOverlap,
        review_status: goldItem?.review_status ?? null,
        category_ids: categoryIds,
        primary_category: primaryReviewCategory(categoryIds),
      }
    }).sort((a, b) => {
      const aMatch = a.matches_reference === false ? 0 : 1
      const bMatch = b.matches_reference === false ? 0 : 1
      if (aMatch !== bMatch) {
        return aMatch - bMatch
      }
      return String(a.requirement_id).localeCompare(String(b.requirement_id), undefined, {numeric: true})
    })
  }, [activeRun, goldById])
  const reviewCategoryCounts = useMemo(() => {
    const counts = new Map<ReviewCategoryId, number>()
    for (const row of comparisonRows) {
      if (row.review_status === 'needs_review') {
        counts.set('needs_review', (counts.get('needs_review') ?? 0) + 1)
      }
      for (const categoryId of row.category_ids) {
        counts.set(categoryId, (counts.get(categoryId) ?? 0) + 1)
      }
    }
    return counts
  }, [comparisonRows])
  const filteredComparisonRows = useMemo(() => {
    if (reviewCategoryId === 'all') {
      return comparisonRows
    }
    return comparisonRows.filter((row) =>
      reviewCategoryId === 'needs_review'
        ? row.review_status === 'needs_review'
        : row.category_ids.includes(reviewCategoryId),
    )
  }, [comparisonRows, reviewCategoryId])
  const comparisonSummary = useMemo(() => {
    const comparedItems = comparisonRows.filter((row) => row.reference_label).length
    const matches = comparisonRows.filter((row) => row.matches_reference === true).length
    return {
      matches,
      compared_items: comparedItems,
      accuracy_on_matched_ids: comparedItems > 0 ? matches / comparedItems : null,
    }
  }, [comparisonRows])

  return (
    <section className="stack-layout">
      <section className="card">
        <div className="panel-header">
          <h3>Verification runs</h3>
          <button className="secondary-button" onClick={() => void refreshRuns()}>
            Refresh runs
          </button>
        </div>
        {runsState === 'loading' && <p className="inline-note">Loading runs...</p>}
        {runMessage && <p className="inline-note">{runMessage}</p>}
        {runs.length > 0 ? (
          <>
            {selectedRunSummary && (
              <div className="selected-verification-run">
                <span className="eyebrow">Selected run</span>
                <strong>{runLabel(selectedRunSummary)}</strong>
                <span>{selectedRunSummary.verifier ?? 'unknown'} · {selectedRunSummary.verifier_model ?? 'default'} · {selectedRunSummary.requirements_count} requirements</span>
                <span className="run-metadata">
                  {selectedRunSummary.has_pipeline_evidence && <span>{selectedRunSummary.evidence_count ?? 0} evidence records</span>}
                  {runHasBboxHint(selectedRunSummary) && <span className="status-pill supported run-evidence-pill">Bounding boxes</span>}
                  {(selectedRunSummary.verifier_failure_count ?? 0) > 0 && (
                    <span className="status-pill missing">{selectedRunSummary.verifier_failure_count} verifier failure(s)</span>
                  )}
                  {(selectedRunSummary.verifier_fallbacks ?? 0) > 0 && (
                    <span className="status-pill abstain">{selectedRunSummary.verifier_fallbacks} fallback(s)</span>
                  )}
                  <span>{formatTimestamp(selectedRunSummary.timestamp)}</span>
                </span>
              </div>
            )}
            <details className="verification-runs-disclosure">
              <summary>
                <span><strong>Browse all verification runs</strong><small>{runs.length} runs available</small></span>
                <span className="disclosure-hint">Expand</span>
              </summary>
              <div className="verification-runs-disclosure-content">
                <label>
                  Select run
                  <select
                    value={selectedRunId}
                    onChange={(event) => {
                      void selectRun(event.target.value)
                    }}
                  >
                    {runs.map((run) => (
                      <option key={run.run_id} value={run.run_id}>
                        {runLabel(run)} | {run.verifier ?? 'unknown'} | {run.retriever ?? 'unknown'} | {run.requirements_count} reqs | {formatDistribution(run.label_distribution)}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="demo-table verification-runs-table">
                  <div className="demo-table-header">
                    <span>Source</span>
                    <span>Verifier</span>
                    <span>Retriever</span>
                    <span>Labels</span>
                  </div>
                  {runs.map((run) => (
                    <button
                      key={run.run_id}
                      className={`demo-table-row comparison-row-button${run.run_id === selectedRunId ? ' selected' : ''}`}
                      onClick={() => void selectRun(run.run_id)}
                    >
                      <span className="review-mini-stack">
                        <strong title={run.path}>{runLabel(run)}</strong>
                        <span title={run.path}>{run.source}</span>
                        <span className="run-metadata">
                          {run.has_pipeline_evidence && <span>{run.evidence_count ?? 0} evidence records</span>}
                          {runHasBboxHint(run) && <span className="status-pill supported run-evidence-pill">Bounding boxes</span>}
                          {(run.verifier_failure_count ?? 0) > 0 && <span className="status-pill missing">Verifier failed</span>}
                          {(run.verifier_fallbacks ?? 0) > 0 && <span>{run.verifier_fallbacks} fallback(s)</span>}
                          <span>{formatTimestamp(run.timestamp)}</span>
                        </span>
                      </span>
                      <span className="review-mini-stack">
                        <strong>{run.verifier ?? 'unknown'}</strong>
                        <span>{run.verifier_model ?? 'default'}</span>
                      </span>
                      <span>{run.retriever ?? 'unknown'}</span>
                      <span className="review-mini-stack">
                        <span>{formatCompactDistribution(run.label_distribution)}</span>
                        <span>{run.metrics_available ? 'metrics available' : 'no metrics file'}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </details>
          </>
        ) : (
          <p className="empty-text">No generated verification pipeline output exists for this flow yet.</p>
        )}
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Run pipeline</h3>
          <span>{usesGeminiVerifier
            ? 'Visual verification uses Gemini and may consume API quota.'
            : 'The lexical baseline does not inspect image content and commonly abstains.'}</span>
        </div>
        <div className="toolbar-grid">
          <label>
            Verifier
            <select
              value={runForm.verifier}
              onChange={(event) => selectVerifier(event.target.value as StartPipelineRunPayload['verifier'])}
            >
              <option value="gemini-image">Visual verification (Gemini)</option>
              <option value="deterministic_rule_based">Lexical baseline (limited)</option>
            </select>
          </label>
          {usesGeminiVerifier && (
            <label>
              Screenshot verifier model
              <select value={runForm.verifier_model} onChange={(event) => setRunForm({...runForm, verifier_model: event.target.value})}>
                {GEMINI_VERIFIER_MODELS.map((model) => <option key={model.value} value={model.value}>{model.label}</option>)}
              </select>
            </label>
          )}
          <label>
            Retriever
            <select
              value={runForm.retriever}
              onChange={(event) => setRunForm({...runForm, retriever: event.target.value as StartPipelineRunPayload['retriever']})}
            >
              <option value="lexical">Lexical / OCR overlap</option>
              <option value="tfidf">TF-IDF text ranking</option>
              <option value="llm">LLM text reranking</option>
            </select>
          </label>
          {runForm.retriever === 'llm' && (
            <>
              <label>
                Retriever provider
                <select
                  value={runForm.retriever_provider}
                  onChange={(event) => {
                    const provider = event.target.value as StartPipelineRunPayload['retriever_provider']
                    setRunForm({...runForm, retriever_provider: provider, retriever_model: defaultTextModel(provider)})
                  }}
                >
                  <option value="deepseek">DeepSeek</option>
                  <option value="gemini">Gemini</option>
                </select>
              </label>
              <label>
                Retriever model
                <select value={runForm.retriever_model} onChange={(event) => setRunForm({...runForm, retriever_model: event.target.value})}>
                  {TEXT_MODELS_BY_PROVIDER[runForm.retriever_provider].map((model) => (
                    <option key={model.value} value={model.value}>{model.label}</option>
                  ))}
                </select>
              </label>
            </>
          )}
          <label>
            Requirement decomposition
            <select
              value={runForm.llm_claim_fallback ? 'llm' : 'rules'}
              onChange={(event) => setRunForm({...runForm, llm_claim_fallback: event.target.value === 'llm'})}
            >
              <option value="rules">Rule-based only</option>
              <option value="llm">LLM-assisted fallback</option>
            </select>
          </label>
          {runForm.llm_claim_fallback && (
            <>
              <label>
                Decomposition provider
                <select
                  value={runForm.claim_provider}
                  onChange={(event) => {
                    const provider = event.target.value as StartPipelineRunPayload['claim_provider']
                    setRunForm({...runForm, claim_provider: provider, claim_model: defaultTextModel(provider)})
                  }}
                >
                  <option value="deepseek">DeepSeek</option>
                  <option value="gemini">Gemini</option>
                </select>
              </label>
              <label>
                Decomposition model
                <select value={runForm.claim_model} onChange={(event) => setRunForm({...runForm, claim_model: event.target.value})}>
                  {TEXT_MODELS_BY_PROVIDER[runForm.claim_provider].map((model) => (
                    <option key={model.value} value={model.value}>{model.label}</option>
                  ))}
                </select>
              </label>
            </>
          )}
          <label>
            Requirements
            <select
              value={runForm.requirements_source}
              onChange={(event) => setRunForm({...runForm, requirements_source: event.target.value as StartPipelineRunPayload['requirements_source']})}
            >
              {defaultRequirementsSource === 'uploaded' ? (
                <option value="uploaded">uploaded requirements</option>
              ) : (
                <>
                  <option value="benchmark">verification benchmark</option>
                  <option value="accepted">accepted requirements</option>
                </>
              )}
            </select>
          </label>
          <label>
            Output directory
            <input value={runForm.output_dir_name} onChange={(event) => setRunForm({...runForm, output_dir_name: event.target.value})} />
          </label>
          <label>
            Retrieved screenshots (top-k)
            <input type="number" min={1} max={20} value={runForm.top_k} onChange={(event) => setRunForm({...runForm, top_k: Number(event.target.value)})} />
          </label>
          <label>
            Max claims per requirement
            <input type="number" min={1} max={10} value={runForm.max_claims} onChange={(event) => setRunForm({...runForm, max_claims: Number(event.target.value)})} />
          </label>
          {usesGeminiVerifier && (
            <>
              <label>
                Max images per claim
                <input type="number" min={1} max={20} value={runForm.max_images} onChange={(event) => setRunForm({...runForm, max_images: Number(event.target.value)})} />
              </label>
              <label>
                Gemini API call limit
                <input
                  type="number"
                  min={-1}
                  max={1000}
                  value={runForm.max_gemini_api_calls}
                  onChange={(event) => setRunForm({...runForm, max_gemini_api_calls: Number(event.target.value)})}
                />
              </label>
              <label>
                Retries for temporary Gemini errors
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={runForm.gemini_max_retries}
                  onChange={(event) => setRunForm({...runForm, gemini_max_retries: Number(event.target.value)})}
                />
              </label>
              <label>
                Reuse cached responses
                <select value={runForm.use_cache ? 'true' : 'false'} onChange={(event) => setRunForm({...runForm, use_cache: event.target.value === 'true'})}>
                  <option value="true">yes</option>
                  <option value="false">no</option>
                </select>
              </label>
            </>
          )}
        </div>
        <p className="inline-note">
          {usesGeminiVerifier
            ? `${runForm.retriever === 'llm' ? 'LLM reranking makes a separate text-model request. ' : ''}${runForm.llm_claim_fallback ? 'LLM-assisted decomposition may make additional text-model requests for compound requirements. ' : ''}Text-model requests are not counted by the Gemini verifier call limit. Gemini evaluates the selected screenshots; failed or capped groups are reported in the run diagnostics below.`
            : 'Use this baseline for offline diagnostics only. It scores lexical/OCR overlap, cannot interpret the screenshots semantically, and is expected to abstain when visible evidence is weak.'}
        </p>
        <div className="button-row">
          <button onClick={() => void startRun()} disabled={runJob?.status === 'running'}>
            {usesGeminiVerifier ? 'Run visual verification' : 'Run lexical baseline'}
          </button>
        </div>
        {runJob && (
          <div className="meta-block">
            <span>Status: {runJob.status}</span>
            <span>Output path: {runJob.output_path ?? 'pending'}</span>
            <span>Return code: {runJob.return_code ?? 'pending'}</span>
            {runJob.recent_log_lines.length > 0 && <pre className="code-block">{runJob.recent_log_lines.slice(-12).join('\n')}</pre>}
          </div>
        )}
        <details className="expandable-section">
          <summary className="expandable-summary">
            <h4>Advanced CLI command</h4>
            <span>Manual equivalent for repository root.</span>
          </summary>
          <pre className="code-block expandable-body">{cliCommand}</pre>
        </details>
      </section>

      {!activeRun && (
        <section className="card">
          <p className="empty-text">Select an existing run or start a new pipeline run to inspect verification output.</p>
        </section>
      )}

      {activeRun && (
        <>
      <section className="card">
        <div className="panel-header">
          <h3>Verification pipeline run</h3>
          <span>{activeRun.flow_id}</span>
        </div>
        {geminiDiagnostics && (
          <div className={`verifier-diagnostics${allGeminiVerificationFailed ? ' error' : ''}`}>
            <strong>{allGeminiVerificationFailed
              ? 'Gemini produced no judgments for this run'
              : 'Gemini verifier diagnostics'}</strong>
            <span>
              {geminiApiCalls} successful API call(s) · {geminiCacheHits} cache hit(s) · {verifierFallbacks} fallback decision(s)
            </span>
            {allGeminiVerificationFailed && (
              <p>Every displayed label came from the rule-based fallback. Treat the resulting MISSING and ABSTAIN labels as a failed verifier run, not as Gemini judgments.</p>
            )}
            {verifierFailures.length > 0 && (
              <details open={allGeminiVerificationFailed}>
                <summary>{verifierFailures.length} verifier failure(s)</summary>
                <ul>
                  {verifierFailures.slice(0, 5).map((failure, index) => (
                    <li key={`${String(failure.group_id ?? 'failure')}-${index}`}>
                      {failure.group_id ? `${String(failure.group_id)}: ` : ''}{String(failure.error ?? 'Unknown verifier failure')}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
        <div className="metric-grid">
          <Metric label="Requirements" value={String(metadata.requirements_count ?? activeRun.results.length)} />
          <Metric label="Claims" value={String(metadata.claim_count ?? activeRun.results.reduce((sum, result) => sum + result.claims.length, 0))} />
          <Metric label="Retriever" value={String(metadata.selected_retriever ?? metadata.retriever ?? metadata.requested_retriever ?? 'unknown')} />
          <Metric label="Claim model" value={String(metadata.claim_model ?? 'rule-based')} />
          <Metric label="Verifier" value={String(metadata.verifier ?? 'deterministic')} />
          <Metric label="Verifier model" value={String(metadata.verifier_model ?? 'rule-based')} />
          <Metric label="Reference matches" value={`${comparisonSummary.matches ?? 'n/a'} / ${comparisonSummary.compared_items ?? 'n/a'}`} />
          <Metric label="Reference accuracy" value={formatMetricValue(comparisonSummary.accuracy_on_matched_ids)} />
        </div>
        <div className="meta-block">
          <span>Labels: {formatDistribution(labelDistribution)}</span>
          <span>Claim statuses: {formatDistribution(claimStatusDistribution)}</span>
          <span>Run source: {String(metadata.run_source ?? metadata.pipeline ?? 'verification_pipeline')}</span>
          <span>Run path: {String(metadata.run_path ?? 'unknown')}</span>
          <span>Requirements: {String(metadata.requirements_path ?? 'unknown')}</span>
          <span>Claim provider: {String(metadata.claim_provider ?? 'rule_based')}</span>
          <span>Top-k: {String(metadata.top_k ?? 'unknown')}</span>
        </div>
      </section>

      {verificationGold.length > 0 && <section className="card">
        <div className="panel-header">
          <h3>Reviewed-label comparison</h3>
          <span>{filteredComparisonRows.length} shown. Disagreement categories include accepted benchmark items.</span>
        </div>
        <div className="review-category-toolbar">
          {REVIEW_CATEGORY_OPTIONS.map((category) => {
            const count = reviewCategoryCounts.get(category.id) ?? 0
            return (
              <button
                key={category.id}
                type="button"
                className={reviewCategoryId === category.id ? 'category-filter active' : 'category-filter'}
                onClick={() => setReviewCategoryId(category.id)}
              >
                <span>{category.label}</span>
                <strong>{count}</strong>
              </button>
            )
          })}
          <button
            type="button"
            className={reviewCategoryId === 'all' ? 'category-filter active' : 'category-filter'}
            onClick={() => setReviewCategoryId('all')}
          >
            <span>All rows</span>
            <strong>{comparisonRows.length}</strong>
          </button>
        </div>
        {comparisonRows.length > 0 ? (
          <div className="demo-table review-comparison-table">
            <div className="demo-table-header">
              <span>Requirement</span>
              <span>Prediction</span>
              <span>Reviewed</span>
              <span>Queue</span>
              <span>Ambiguity</span>
              <span>Claim composition</span>
              <span>Evidence</span>
              <span>Review</span>
            </div>
            {filteredComparisonRows.map((row) => {
              const requirementId = row.requirement_id
              const result = resultById.get(requirementId)
              const goldItem = goldById.get(requirementId)
              const canAccept = Boolean(
                result &&
                  goldItem &&
                  goldItem.review_status === 'needs_review' &&
                  canEditBenchmarkItemFromRun(result, goldItem),
              )
              return (
                <div
                  key={requirementId}
                  className="demo-table-row comparison-row-button"
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedRequirementId(requirementId)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      setSelectedRequirementId(requirementId)
                    }
                  }}
                >
                  <strong>{requirementId}</strong>
                  <span className={`status-pill ${statusClass(row.predicted_label ?? 'unknown')}`}>{humanizeStatus(row.predicted_label ?? 'unknown')}</span>
                  <span className={`status-pill ${statusClass(row.reference_label ?? 'unknown')}`}>{humanizeStatus(row.reference_label ?? 'unknown')}</span>
                  <span className="review-mini-stack">
                    <strong>{reviewCategoryLabel(row.primary_category)}</strong>
                    <span>{row.review_status ? humanizeStatus(row.review_status) : 'no benchmark item'}</span>
                  </span>
                  <span className="review-mini-stack">
                    <strong>Manual</strong>
                    <span title={formatReasons(goldItem?.uncertainty_reasons ?? [])}>{formatReasons(goldItem?.uncertainty_reasons ?? [])}</span>
                    <strong>Pipeline</strong>
                    <span title={formatReasons(result?.uncertainty_reasons ?? [])}>{formatReasons(result?.uncertainty_reasons ?? [])}</span>
                  </span>
                  <span className="review-mini-stack">
                    <strong>Manual</strong>
                    <span title={formatDistribution(claimStatusDistributionForGoldClaims(goldItem?.claims ?? []))}>
                      {formatCompactDistribution(claimStatusDistributionForGoldClaims(goldItem?.claims ?? []))}
                    </span>
                    <strong>Pipeline</strong>
                    <span title={formatDistribution(claimStatusDistributionForPipelineClaims(result?.claims ?? []))}>
                      {formatCompactDistribution(claimStatusDistributionForPipelineClaims(result?.claims ?? []))}
                    </span>
                  </span>
                  <span>
                    <span className="review-mini-stack">
                      <strong>Manual</strong>
                      <span><StepChipList stepIndices={(row.reference_evidence_steps ?? []) as number[]} onJumpToStep={onJumpToStep} /></span>
                      <strong>Pipeline</strong>
                      <span><StepChipList stepIndices={(row.predicted_evidence_steps ?? []) as number[]} onJumpToStep={onJumpToStep} /></span>
                    </span>
                  </span>
                  <span className="button-row compact">
                    {goldItem?.review_status === 'needs_review' && (
                      <button
                        type="button"
                        className="secondary-button"
                        disabled={!canAccept || acceptingRequirementId === requirementId}
                        title={canAccept ? 'Accept this open benchmark item' : 'Benchmark item is missing or changed since this run'}
                        onClick={(event) => {
                          event.stopPropagation()
                          if (goldItem && canAccept) {
                            void acceptBenchmarkItem(goldItem)
                          }
                        }}
                      >
                        {acceptingRequirementId === requirementId ? 'Accepting...' : 'Accept'}
                      </button>
                    )}
                  </span>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="empty-text">No reviewed reference comparison was available.</p>
        )}
      </section>}

      <section className="card">
        <div className="panel-header">
          <h3>Requirement decisions</h3>
          <span>Each decision includes claim-level evidence.</span>
        </div>
        <div className="requirement-list">
          {activeRun.results.map((result) => (
            <article key={result.requirement_id} className="requirement-card">
              <div className="requirement-header">
                <strong>{result.requirement_id}</strong>
                <div className="pill-row">
                  <span className={`status-pill ${statusClass(result.final_label)}`}>{humanizeStatus(result.final_label)}</span>
                  <span className={`status-pill ${statusClass(result.ui_evaluability)}`}>{humanizeStatus(result.ui_evaluability)}</span>
                </div>
              </div>
              <p>{result.requirement_text}</p>
              <div className="meta-block">
                <span>Evidence steps: <StepChipList stepIndices={uniqueEvidenceSteps(result.evidence)} onJumpToStep={onJumpToStep} /></span>
                <span>Uncertainty: {result.uncertainty_reasons.map(humanizeStatus).join(', ') || 'none'}</span>
              </div>
              <p className="inline-note">Rationale: {result.rationale}</p>
              <div className="claim-summary">
                {result.claims.map((claim) => (
                  <div key={claim.claim_id} className="claim-summary-row">
                    <span className={`status-pill ${statusClass(claim.status)}`}>{humanizeStatus(claim.status)}</span>
                    <span>{claim.claim_text}</span>
                    <span className="mini-label">steps <StepChipList stepIndices={uniqueEvidenceSteps(claim.evidence)} onJumpToStep={onJumpToStep} /></span>
                  </div>
                ))}
              </div>
              <div className="button-row left">
                <button className="secondary-button" onClick={() => setSelectedRequirementId(result.requirement_id)}>
                  {goldById.get(result.requirement_id) ? 'Inspect manual vs pipeline' : 'Inspect evidence & bounding boxes'}
                </button>
                {goldById.get(result.requirement_id) && (
                  <button
                    className="secondary-button"
                    disabled={!canEditBenchmarkItemFromRun(result, goldById.get(result.requirement_id) as VerificationGoldItem)}
                    title={
                      canEditBenchmarkItemFromRun(result, goldById.get(result.requirement_id) as VerificationGoldItem)
                        ? 'Edit current verification benchmark item'
                        : 'Benchmark item text changed since this run'
                    }
                    onClick={() => {
                      const goldItem = goldById.get(result.requirement_id)
                      if (goldItem && canEditBenchmarkItemFromRun(result, goldItem)) {
                        onEditVerificationGold(goldItem)
                      }
                    }}
                  >
                    Edit benchmark item
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
        </>
      )}
      {selectedResult && (
        <VerificationComparisonModal
          result={selectedResult}
          gold={selectedGold}
          steps={steps}
          onClose={() => setSelectedRequirementId(null)}
          onJumpToStep={onJumpToStep}
          onEditBenchmarkItem={
            selectedGold && canEditBenchmarkItemFromRun(selectedResult, selectedGold)
              ? () => {
                  onEditVerificationGold(selectedGold)
                  setSelectedRequirementId(null)
                }
              : undefined
          }
          onAcceptBenchmarkItem={
            selectedGold &&
            selectedGold.review_status === 'needs_review' &&
            canEditBenchmarkItemFromRun(selectedResult, selectedGold)
              ? () => acceptBenchmarkItem(selectedGold)
              : undefined
          }
          accepting={acceptingRequirementId === selectedGold?.requirement_id}
        />
      )}
    </section>
  )
}

function VerificationComparisonModal({
  result,
  gold,
  steps,
  onClose,
  onJumpToStep,
  onEditBenchmarkItem,
  onAcceptBenchmarkItem,
  accepting,
}: {
  result: PipelineResult
  gold: VerificationGoldItem | null
  steps: FlowStep[]
  onClose: () => void
  onJumpToStep: (stepIndex: number) => void
  onEditBenchmarkItem?: () => void
  onAcceptBenchmarkItem?: () => void
  accepting: boolean
}) {
  const goldLabel = normalizeDisplayValue(gold?.verification_label)
  const predictedLabel = normalizeDisplayValue(result.final_label)
  const labelMismatch = goldLabel !== 'unknown' && goldLabel !== predictedLabel
  const falseFulfillment = predictedLabel === 'FULFILLED' && goldLabel !== 'FULFILLED' && goldLabel !== 'unknown'
  const predictedEvidenceSteps = uniqueEvidenceSteps(result.evidence)
  const goldEvidenceSteps = gold?.evidence_steps ?? []
  const evidenceOverlap = intersectNumbers(goldEvidenceSteps, predictedEvidenceSteps)
  const alignments = alignClaims(gold?.claims ?? [], result.claims)
  const manualClaimDistribution = claimStatusDistributionForGoldClaims(gold?.claims ?? [])
  const pipelineClaimDistribution = claimStatusDistributionForPipelineClaims(result.claims)
  const rootFindings = comparisonFindings({
    gold,
    result,
    goldLabel,
    predictedLabel,
    falseFulfillment,
    labelMismatch,
    evidenceOverlap,
    alignments,
  })

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card comparison-modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header align-start">
          <div>
            <h3>{gold ? 'Manual vs pipeline comparison' : 'Evidence inspection'}</h3>
            <span>{result.requirement_id}</span>
          </div>
          <div className="button-row wrap">
            {gold && <button
                type="button"
                className="secondary-button"
                disabled={!onEditBenchmarkItem}
                title={onEditBenchmarkItem ? 'Edit current verification benchmark item' : 'Benchmark item changed since this run'}
                onClick={onEditBenchmarkItem}
              >
                Edit benchmark item
              </button>}
            {onAcceptBenchmarkItem && (
              <button type="button" disabled={accepting} title="Accept this verification benchmark item" onClick={onAcceptBenchmarkItem}>
                {accepting ? 'Accepting...' : 'Accept item'}
              </button>
            )}
            <button type="button" className="secondary-button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <section className={falseFulfillment ? 'comparison-hero high-risk' : 'comparison-hero'}>
          <div>
            <span className="mini-label">Requirement</span>
            <p>{gold?.text ?? result.requirement_text}</p>
          </div>
          <div className={gold ? 'comparison-verdict-strip' : 'comparison-verdict-strip pipeline-only'}>
            {gold && <div>
              <span>Manual benchmark</span>
              <strong className={`status-pill ${statusClass(goldLabel)}`}>{humanizeStatus(goldLabel)}</strong>
            </div>}
            <div>
              <span>Pipeline decision</span>
              <strong className={`status-pill ${statusClass(predictedLabel)}`}>{humanizeStatus(predictedLabel)}</strong>
            </div>
            <div>
              <span>{gold ? 'Risk' : 'Evidence screens'}</span>
              <strong>{gold ? (falseFulfillment ? 'False fulfillment' : labelMismatch ? 'Label mismatch' : 'Label aligned') : (predictedEvidenceSteps.join(', ') || 'None')}</strong>
            </div>
          </div>
        </section>

        <section className="comparison-section">
          <div className="panel-header">
            <h4>Final label and claim composition</h4>
            <span>The pipeline label is produced by the aggregation step, not by copying one claim.</span>
          </div>
          <div className={gold ? 'composition-grid' : 'composition-grid pipeline-only'}>
            {gold && <article className="composition-card">
              <span className="mini-label">Manual final label</span>
              <strong className={`status-pill ${statusClass(goldLabel)}`}>{humanizeStatus(goldLabel)}</strong>
              <p>Claim labels: {formatDistribution(manualClaimDistribution)}</p>
              <p>Ambiguity: {formatReasons(gold?.uncertainty_reasons ?? [])}</p>
            </article>}
            <article className="composition-card">
              <span className="mini-label">Pipeline final label</span>
              <strong className={`status-pill ${statusClass(predictedLabel)}`}>{humanizeStatus(predictedLabel)}</strong>
              <p>Claim labels: {formatDistribution(pipelineClaimDistribution)}</p>
              <p>Ambiguity: {formatReasons(result.uncertainty_reasons)}</p>
            </article>
            <article className="composition-card aggregation-card">
              <span className="mini-label">Aggregation rule</span>
              <p>
                Contradicted central observable claims become not fulfilled. Supported or partially supported central observable claims can become fulfilled.
                Mixed supported and missing, hidden, or ambiguous important claims become partially fulfilled. Missing evidence or non-UI-verifiable requirements abstain.
              </p>
            </article>
          </div>
        </section>

        <section className="comparison-grid">
          {gold && <ComparisonColumn
            title="Manual benchmark"
            label={goldLabel}
            uiEvaluability={gold?.ui_evaluability}
            uncertaintyReasons={gold?.uncertainty_reasons ?? []}
            evidenceSteps={goldEvidenceSteps}
            rationale={gold?.rationale}
            evidenceNote={gold?.evidence_note}
            onJumpToStep={onJumpToStep}
          />}
          <ComparisonColumn
            title="Pipeline output"
            label={predictedLabel}
            uiEvaluability={result.ui_evaluability}
            uncertaintyReasons={result.uncertainty_reasons}
            evidenceSteps={predictedEvidenceSteps}
            rationale={result.rationale}
            evidenceNote={undefined}
            onJumpToStep={onJumpToStep}
          />
        </section>

        {gold && <section className="comparison-section">
          <div className="panel-header">
            <h4>Why the decision differs</h4>
            <span>Evidence overlap: {evidenceOverlap.length > 0 ? evidenceOverlap.join(', ') : 'none'}</span>
          </div>
          <div className="finding-list">
            {rootFindings.map((finding) => (
              <div key={finding} className="finding-card">
                {finding}
              </div>
            ))}
          </div>
        </section>}

        <section className="comparison-section">
          <div className="panel-header">
            <div>
              <h4>{gold ? 'Claim alignment' : 'Claim evidence'}</h4>
              <span>{gold ? 'Manual claims are aligned to pipeline claims by token overlap.' : 'Inspect retrieved evidence and localized regions for each pipeline claim.'}</span>
            </div>
            {onAcceptBenchmarkItem && (
              <button type="button" disabled={accepting} title="Accept this verification benchmark item" onClick={onAcceptBenchmarkItem}>
                {accepting ? 'Accepting...' : 'Accept item'}
              </button>
            )}
          </div>
          <div className="claim-alignment-list">
            {alignments.map((alignment, index) => (
              <ClaimAlignmentRow
                key={`${result.requirement_id}-alignment-${index}`}
                alignment={alignment}
                steps={steps}
                onJumpToStep={onJumpToStep}
                pipelineOnly={!gold}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

function ComparisonColumn({
  title,
  label,
  uiEvaluability,
  uncertaintyReasons,
  evidenceSteps,
  rationale,
  evidenceNote,
  onJumpToStep,
}: {
  title: string
  label: string
  uiEvaluability?: string | null
  uncertaintyReasons: string[]
  evidenceSteps: number[]
  rationale?: string | null
  evidenceNote?: string | null
  onJumpToStep: (stepIndex: number) => void
}) {
  return (
    <article className="comparison-column">
      <div className="comparison-column-header">
        <h4>{title}</h4>
        <span className={`status-pill ${statusClass(label)}`}>{humanizeStatus(label)}</span>
      </div>
      <div className="meta-block">
        <span>UI evaluability: {uiEvaluability ? humanizeStatus(uiEvaluability) : 'unknown'}</span>
        <span>Ambiguity: {uncertaintyReasons.length > 0 ? uncertaintyReasons.map(humanizeStatus).join(', ') : 'none'}</span>
        <span>Evidence: <StepChipList stepIndices={evidenceSteps} onJumpToStep={onJumpToStep} /></span>
      </div>
      {evidenceNote && <p className="inline-note">Evidence note: {evidenceNote}</p>}
      {rationale && <p className="inline-note">Rationale: {rationale}</p>}
    </article>
  )
}

function ClaimAlignmentRow({
  alignment,
  steps,
  onJumpToStep,
  pipelineOnly = false,
}: {
  alignment: ClaimAlignment
  steps: FlowStep[]
  onJumpToStep: (stepIndex: number) => void
  pipelineOnly?: boolean
}) {
  const goldClaim = alignment.goldClaim
  const predictedClaim = alignment.predictedClaim
  const statusMismatch = normalizeDisplayValue(goldClaim?.status) !== normalizeDisplayValue(predictedClaim?.status)
  const goldEvidenceUnit = firstRegionEvidenceUnit(goldClaim?.evidence_units)
  const pipelineEvidenceByStep = groupPipelineEvidenceByStep(predictedClaim?.evidence ?? [])
  return (
    <article className={`${statusMismatch && !pipelineOnly ? 'claim-alignment-row status-mismatch' : 'claim-alignment-row'}${pipelineOnly ? ' pipeline-only' : ''}`}>
      {!pipelineOnly && <div className="alignment-score">
        <span>match</span>
        <strong>{alignment.score.toFixed(2)}</strong>
      </div>}
      {!pipelineOnly && <div className="aligned-claim manual">
        <div className="comparison-column-header">
          <strong>Manual claim</strong>
          {goldClaim?.status && <span className={`status-pill ${statusClass(goldClaim.status)}`}>{humanizeStatus(goldClaim.status)}</span>}
        </div>
        <p>{goldClaim ? goldClaim.claim_text ?? goldClaim.claim : 'No matched manual claim.'}</p>
        {goldClaim && (
          <div className="meta-block">
            <span>Type: {goldClaim.claim_type ? humanizeStatus(goldClaim.claim_type) : 'unknown'}</span>
            <span>Importance: {goldClaim.importance ? humanizeStatus(goldClaim.importance) : 'unknown'}</span>
            <span>Evidence: <StepChipList stepIndices={goldClaim.evidence_steps ?? []} onJumpToStep={onJumpToStep} /></span>
            {goldClaim.uncertainty_reasons && goldClaim.uncertainty_reasons.length > 0 && (
              <span>Ambiguity: {goldClaim.uncertainty_reasons.map(humanizeStatus).join(', ')}</span>
            )}
          </div>
        )}
        {goldClaim?.note && <p className="inline-note">{goldClaim.note}</p>}
        {goldEvidenceUnit && (
          <EvidenceBoxPreview
            step={steps.find((step) => step.step_index === goldEvidenceUnit.step_index) ?? null}
            bbox={goldEvidenceUnit.bbox ?? null}
            label={`Manual box · step ${goldEvidenceUnit.step_index}`}
            bboxMetadata={metadataFromEvidenceUnit(goldEvidenceUnit)}
            legacyVariant="display"
          />
        )}
      </div>}
      <div className="aligned-claim predicted">
        <div className="comparison-column-header">
          <strong>Pipeline claim</strong>
          {predictedClaim?.status && <span className={`status-pill ${statusClass(predictedClaim.status)}`}>{humanizeStatus(predictedClaim.status)}</span>}
        </div>
        <p>{predictedClaim?.claim_text ?? 'No matched pipeline claim.'}</p>
        {predictedClaim && (
          <>
            <div className="meta-block">
              <span>Core: {String(predictedClaim.is_core)}</span>
              <span>Observable: {String(predictedClaim.is_observable)}</span>
              <span>Confidence: {predictedClaim.confidence === null || predictedClaim.confidence === undefined ? 'unknown' : predictedClaim.confidence.toFixed(3)}</span>
              <span>Evidence: <StepChipList stepIndices={uniqueEvidenceSteps(predictedClaim.evidence)} onJumpToStep={onJumpToStep} /></span>
              {predictedClaim.uncertainty_reasons.length > 0 && (
                <span>Ambiguity: {predictedClaim.uncertainty_reasons.map(humanizeStatus).join(', ')}</span>
              )}
            </div>
            <p className="inline-note">Rationale: {predictedClaim.rationale}</p>
            <div className="evidence-snippet-list">
              {pipelineEvidenceByStep.slice(0, 3).map((evidenceGroup) => {
                const regions = evidenceGroup.evidence.flatMap((evidence) => {
                  const bbox = normalizeBoundingBox(evidence.bbox)
                  return bbox ? [{bbox, bboxMetadata: metadataFromPipelineEvidence(evidence)}] : []
                })
                return (
                  <div key={`${predictedClaim.claim_id}-${evidenceGroup.stepIndex}`} className="evidence-snippet-group">
                    <button className="evidence-snippet" onClick={() => onJumpToStep(evidenceGroup.stepIndex)}>
                      <strong>Step {evidenceGroup.stepIndex}</strong>
                      <span>{truncateText(evidenceGroup.evidence.map((evidence) => evidence.visible_observation).filter(Boolean).join(' · '), 260)}</span>
                    </button>
                    {regions.length > 0 && (
                      <EvidenceBoxesPreview
                        step={steps.find((step) => step.step_index === evidenceGroup.stepIndex) ?? null}
                        regions={regions}
                        label={regions.length === 1 ? 'Pipeline box' : `${regions.length} pipeline boxes`}
                        legacyVariant="preview"
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>
    </article>
  )
}

function groupPipelineEvidenceByStep(evidence: PipelineEvidenceItem[]): Array<{stepIndex: number; evidence: PipelineEvidenceItem[]}> {
  const byStep = new Map<number, PipelineEvidenceItem[]>()
  for (const item of evidence) {
    byStep.set(item.step_index, [...(byStep.get(item.step_index) ?? []), item])
  }
  return [...byStep.entries()]
    .sort((left, right) => left[0] - right[0])
    .map(([stepIndex, groupedEvidence]) => ({stepIndex, evidence: groupedEvidence}))
}

function Metric({label, value}: {label: string; value: string}) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong title={value}>{value}</strong>
    </div>
  )
}

function formatMetricValue(value: unknown): string {
  if (typeof value !== 'number') {
    return value === undefined || value === null ? 'n/a' : String(value)
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(3)
}

function formatDistribution(distribution: Record<string, number>): string {
  const entries = Object.entries(distribution)
  if (entries.length === 0) {
    return 'none'
  }
  return entries.map(([key, value]) => `${humanizeStatus(key)}: ${value}`).join(', ')
}

function formatCompactDistribution(distribution: Record<string, number>): string {
  const entries = Object.entries(distribution)
  if (entries.length === 0) {
    return 'none'
  }
  return entries.map(([key, value]) => `${humanizeStatus(key)} ${value}`).join(' · ')
}

function formatTimestamp(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return 'unknown time'
  }
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
  if (Number.isNaN(date.getTime())) {
    return String(value)
  }
  return date.toLocaleString()
}

function runLabel(run: PipelineRunSummary): string {
  return run.run_name || fileNameFromPath(run.path) || run.source || run.run_id
}

function fileNameFromPath(path: string | null | undefined): string {
  if (!path) {
    return ''
  }
  const parts = path.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? path
}

function runHasBboxHint(run: PipelineRunSummary): boolean {
  if (run.has_bbox_evidence || Number(run.bbox_evidence_count ?? 0) > 0) {
    return true
  }
  const label = `${runLabel(run)} ${run.path ?? ''}`.toLowerCase()
  return label.includes('with_bboxes') || label.includes('bbox')
}

function orderPipelineRunsForDisplay(runs: PipelineRunSummary[]): PipelineRunSummary[] {
  return [...runs].sort((left, right) => {
    const leftBbox = runHasBboxHint(left) ? 1 : 0
    const rightBbox = runHasBboxHint(right) ? 1 : 0
    if (leftBbox !== rightBbox) {
      return rightBbox - leftBbox
    }
    return Number(right.mtime ?? 0) - Number(left.mtime ?? 0)
  })
}

function formatReasons(reasons: string[]): string {
  return reasons.length > 0 ? reasons.map(humanizeStatus).join(', ') : 'none'
}

function labelDistributionForResults(results: PipelineVerificationRun['results']): Record<string, number> {
  return results.reduce<Record<string, number>>((distribution, result) => {
    distribution[result.final_label] = (distribution[result.final_label] ?? 0) + 1
    return distribution
  }, {})
}

function claimStatusDistributionForResults(results: PipelineVerificationRun['results']): Record<string, number> {
  return results.reduce<Record<string, number>>((distribution, result) => {
    mergeDistribution(distribution, claimStatusDistributionForPipelineClaims(result.claims))
    return distribution
  }, {})
}

function claimStatusDistributionForPipelineClaims(claims: PipelineClaim[]): Record<string, number> {
  return statusDistribution(claims.map((claim) => claim.status))
}

function claimStatusDistributionForGoldClaims(claims: VerificationClaim[]): Record<string, number> {
  return statusDistribution(claims.map((claim) => claim.status))
}

function statusDistribution(values: Array<string | null | undefined>): Record<string, number> {
  return values.reduce<Record<string, number>>((distribution, value) => {
    const normalized = normalizeDisplayValue(value)
    if (normalized !== 'unknown') {
      distribution[normalized] = (distribution[normalized] ?? 0) + 1
    }
    return distribution
  }, {})
}

function mergeDistribution(target: Record<string, number>, source: Record<string, number>) {
  for (const [key, value] of Object.entries(source)) {
    target[key] = (target[key] ?? 0) + value
  }
}

function normalizeDisplayValue(value: unknown): string {
  return typeof value === 'string' && value.trim() ? value.trim().toUpperCase().replace(/-/g, '_').replace(/ /g, '_') : 'unknown'
}

function normalizeRequirementText(value: string | null | undefined): string {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}

function canEditBenchmarkItemFromRun(result: PipelineResult, gold: VerificationGoldItem): boolean {
  return normalizeRequirementText(result.requirement_text) === normalizeRequirementText(gold.text)
}

function reviewCategoriesForComparison(
  gold: VerificationGoldItem | null,
  result: PipelineResult,
  evidenceOverlap: number[],
): ReviewCategoryId[] {
  const categories: ReviewCategoryId[] = []
  if (!gold) {
    return categories
  }

  const goldLabel = normalizeDisplayValue(gold.verification_label)
  const predictedLabel = normalizeDisplayValue(result.final_label)
  const labelMismatch = goldLabel !== 'unknown' && predictedLabel !== 'unknown' && goldLabel !== predictedLabel
  const goldEvidenceSteps = gold.evidence_steps ?? []

  if (labelMismatch) {
    categories.push('label_mismatch')
  }
  if (goldEvidenceSteps.length > 0 && evidenceOverlap.length === 0) {
    categories.push('evidence_no_overlap')
  }
  if (predictedLabel === 'FULFILLED' && goldLabel !== 'FULFILLED' && goldLabel !== 'unknown') {
    categories.push('over_fulfilled')
  }
  if (goldLabel === 'ABSTAIN' && predictedLabel !== 'ABSTAIN' && predictedLabel !== 'unknown') {
    categories.push('should_abstain')
  }
  if (['ABSTAIN', 'NOT_FULFILLED'].includes(predictedLabel) && ['FULFILLED', 'PARTIALLY_FULFILLED'].includes(goldLabel)) {
    categories.push('under_called')
  }
  if (labelMismatch && !categories.includes('over_fulfilled') && !categories.includes('should_abstain') && !categories.includes('under_called')) {
    categories.push('boundary')
  }
  if (isLateStateRequirement(gold.text)) {
    categories.push('late_state')
  }
  if (isUniversalOrHiddenRequirement(gold)) {
    categories.push('universal_or_hidden')
  }
  return [...new Set(categories)]
}

function primaryReviewCategory(categories: ReviewCategoryId[]): ReviewCategoryId {
  const priority: ReviewCategoryId[] = [
    'over_fulfilled',
    'should_abstain',
    'under_called',
    'boundary',
    'evidence_no_overlap',
    'late_state',
    'universal_or_hidden',
    'label_mismatch',
  ]
  return priority.find((category) => categories.includes(category)) ?? 'needs_review'
}

function reviewCategoryLabel(category: ReviewCategoryId): string {
  if (category === 'all') {
    return 'All rows'
  }
  return REVIEW_CATEGORY_OPTIONS.find((option) => option.id === category)?.label ?? humanizeStatus(category)
}

function isLateStateRequirement(text: string): boolean {
  return containsAny(text, [
    'cart',
    'checkout',
    'subtotal',
    'total',
    'fee',
    'tax',
    'payment',
    'purchase',
    'order',
    'result',
    'results',
    'summary',
    'review',
    'confirmation',
    'confirm',
    'pre-checkout',
    'pre-submission',
  ])
}

function isUniversalOrHiddenRequirement(gold: VerificationGoldItem): boolean {
  const textMatches = containsAny(gold.text, [
    'all ',
    'every',
    'only when',
    'distinguish',
    'compare',
    'each',
    'complete',
    'valid',
    'available',
    'future',
    'preserve',
    'persist',
    'return',
    'stored',
    'backend',
    'account',
    'email',
    'external',
  ])
  const claimMatches = (gold.claims ?? []).some((claim) =>
    normalizeDisplayValue(claim.claim_type) === 'HIDDEN' || normalizeDisplayValue(claim.status) === 'HIDDEN',
  )
  return textMatches || claimMatches
}

function containsAny(value: string, needles: string[]): boolean {
  const normalized = value.toLowerCase()
  return needles.some((needle) => normalized.includes(needle))
}

function candidateIdsRepresentedInVerificationGold(items: VerificationGoldItem[]): Set<string> {
  const ids = new Set<string>()
  for (const item of items) {
    ids.add(item.requirement_id)
    if (item.source_candidate_id) {
      ids.add(item.source_candidate_id)
    }
    if (item.source_type === 'requirements_candidate' && item.source_id) {
      ids.add(item.source_id)
    }
  }
  return ids
}

function intersectNumbers(left: number[], right: number[]): number[] {
  const rightSet = new Set(right)
  return left.filter((value) => rightSet.has(value))
}

function alignClaims(goldClaims: VerificationClaim[], predictedClaims: PipelineClaim[]): ClaimAlignment[] {
  const usedPredictions = new Set<number>()
  const alignments: ClaimAlignment[] = []

  for (const goldClaim of goldClaims) {
    let bestIndex = -1
    let bestScore = 0
    predictedClaims.forEach((predictedClaim, index) => {
      if (usedPredictions.has(index)) {
        return
      }
      const score = tokenF1(goldClaim.claim_text ?? goldClaim.claim, predictedClaim.claim_text)
      if (score > bestScore) {
        bestScore = score
        bestIndex = index
      }
    })
    if (bestIndex >= 0 && bestScore >= 0.15) {
      usedPredictions.add(bestIndex)
      alignments.push({goldClaim, predictedClaim: predictedClaims[bestIndex], score: bestScore})
    } else {
      alignments.push({goldClaim, predictedClaim: null, score: 0})
    }
  }

  predictedClaims.forEach((predictedClaim, index) => {
    if (!usedPredictions.has(index)) {
      alignments.push({goldClaim: null, predictedClaim, score: 0})
    }
  })

  return alignments
}

function tokenF1(left: string, right: string): number {
  const leftTokens = tokenize(left)
  const rightTokens = tokenize(right)
  if (leftTokens.length === 0 || rightTokens.length === 0) {
    return 0
  }
  const rightSet = new Set(rightTokens)
  const overlap = leftTokens.filter((token) => rightSet.has(token)).length
  if (overlap === 0) {
    return 0
  }
  const precision = overlap / rightTokens.length
  const recall = overlap / leftTokens.length
  return (2 * precision * recall) / (precision + recall)
}

function tokenize(value: string): string[] {
  return value.toLowerCase().match(/[a-z0-9]+/g) ?? []
}

function comparisonFindings({
  gold,
  result,
  goldLabel,
  predictedLabel,
  falseFulfillment,
  labelMismatch,
  evidenceOverlap,
  alignments,
}: {
  gold: VerificationGoldItem | null
  result: PipelineResult
  goldLabel: string
  predictedLabel: string
  falseFulfillment: boolean
  labelMismatch: boolean
  evidenceOverlap: number[]
  alignments: ClaimAlignment[]
}): string[] {
  const findings: string[] = []
  if (!gold) {
    findings.push('No manual verification benchmark item was found for this pipeline result.')
    return findings
  }
  if (falseFulfillment) {
    findings.push(`Safety issue: the pipeline predicted ${humanizeStatus(predictedLabel)} while the manual benchmark is ${humanizeStatus(goldLabel)}.`)
  } else if (labelMismatch) {
    findings.push(`Label mismatch: manual benchmark is ${humanizeStatus(goldLabel)}, pipeline is ${humanizeStatus(predictedLabel)}.`)
  } else {
    findings.push('Requirement-level label matches the manual benchmark.')
  }

  if (normalizeDisplayValue(gold.ui_evaluability) !== normalizeDisplayValue(result.ui_evaluability)) {
    findings.push(`UI evaluability differs: manual is ${humanizeStatus(normalizeDisplayValue(gold.ui_evaluability))}, pipeline is ${humanizeStatus(result.ui_evaluability)}.`)
  }

  const goldUncertainty = new Set((gold.uncertainty_reasons ?? []).map(normalizeDisplayValue))
  const predictedUncertainty = new Set(result.uncertainty_reasons.map(normalizeDisplayValue))
  const missingUncertainty = [...goldUncertainty].filter((reason) => !predictedUncertainty.has(reason))
  if (missingUncertainty.length > 0) {
    findings.push(`Pipeline missed manual ambiguity reasons: ${missingUncertainty.map(humanizeStatus).join(', ')}.`)
  }

  const goldBlockingClaims = (gold.claims ?? []).filter((claim) =>
    ['CONTRADICTED', 'MISSING', 'HIDDEN', 'AMBIGUOUS', 'OUT_OF_SCOPE', 'PARTIALLY_SUPPORTED'].includes(normalizeDisplayValue(claim.status)),
  )
  const predictedSupportedCount = result.claims.filter((claim) => normalizeDisplayValue(claim.status) === 'SUPPORTED').length
  if (goldBlockingClaims.length > 0 && predictedSupportedCount === result.claims.length) {
    findings.push('Manual benchmark contains blocking or incomplete claims, but every pipeline claim is marked supported.')
  }

  const statusMismatches = alignments.filter(
    (alignment) =>
      alignment.goldClaim &&
      alignment.predictedClaim &&
      normalizeDisplayValue(alignment.goldClaim.status) !== normalizeDisplayValue(alignment.predictedClaim.status),
  )
  if (statusMismatches.length > 0) {
    findings.push(`${statusMismatches.length} aligned claim(s) have different manual and pipeline statuses.`)
  }

  if (evidenceOverlap.length === 0 && gold.evidence_steps.length > 0) {
    findings.push('Pipeline evidence does not overlap with manual evidence steps.')
  }

  if (findings.length === 0) {
    findings.push('No obvious disagreement root was detected from labels, ambiguity, claim status, or evidence overlap.')
  }
  return findings
}

function truncateText(value: string, maxLength: number): string {
  if (value.length <= maxLength) {
    return value
  }
  return `${value.slice(0, maxLength).trim()}...`
}

function uniqueEvidenceSteps(evidence: {step_index: number}[]): number[] {
  return [...new Set(evidence.map((item) => item.step_index))].sort((a, b) => a - b)
}

function normalizeBoundingBox(value: unknown): BoundingBox | null {
  if (Array.isArray(value) && value.length === 4) {
    const [x1, y1, x2, y2] = value.map(Number)
    return validBoundingBox({x1, y1, x2, y2})
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return validBoundingBox({
      x1: Number(record.x1),
      y1: Number(record.y1),
      x2: Number(record.x2),
      y2: Number(record.y2),
    })
  }
  return null
}

function validBoundingBox(box: BoundingBox): BoundingBox | null {
  if ([box.x1, box.y1, box.x2, box.y2].some((value) => !Number.isFinite(value))) {
    return null
  }
  return box.x2 > box.x1 && box.y2 > box.y1 ? box : null
}

function firstRegionEvidenceUnit(units: EvidenceUnit[] | undefined): EvidenceUnit | null {
  return units?.find((unit) => unit.evidence_type === 'region' && normalizeBoundingBox(unit.bbox)) ?? null
}

function claimEvidenceUnitsForPayload(claim: ClaimFormState): EvidenceUnit[] {
  const steps = new Set(claim.evidenceSteps)
  if (claim.evidenceUnit?.bbox) {
    steps.add(claim.evidenceUnit.step_index)
  }
  return [...steps].sort((a, b) => a - b).map((stepIndex) => {
    if (claim.evidenceUnit?.bbox && claim.evidenceUnit.step_index === stepIndex) {
      return {
        ...claim.evidenceUnit,
        evidence_type: 'region',
        bbox: claim.evidenceUnit.bbox,
      }
    }
    return {
    step_index: stepIndex,
    evidence_type: 'screen',
    }
  })
}

function metadataFromEvidenceUnit(unit: EvidenceUnit | null): BoundingBoxMetadata | null {
  if (!unit) {
    return null
  }
  return {
    image_path: unit.bbox_image_path ?? null,
    image_width: unit.bbox_image_width ?? null,
    image_height: unit.bbox_image_height ?? null,
    coordinate_space: unit.bbox_coordinate_space ?? null,
    source: unit.bbox_source ?? null,
    confidence: unit.bbox_confidence ?? null,
    matched_text: unit.matched_text ?? null,
  }
}

function metadataFromPipelineEvidence(evidence: {bbox_metadata?: BoundingBoxMetadata | null; metadata?: {bbox_localization?: BoundingBoxMetadata | null} | null}): BoundingBoxMetadata | null {
  return evidence.bbox_metadata ?? evidence.metadata?.bbox_localization ?? null
}

function RequirementCard({
  requirement,
  actions,
  onJumpToStep,
}: {
  requirement: RequirementLike
  actions?: ReactNode
  onJumpToStep: (stepIndex: number) => void
}) {
  const finalLabel = 'verification_label' in requirement ? requirement.verification_label : requirement.manual_verification_label
  const intendedLabel = 'intended_label' in requirement ? requirement.intended_label : undefined
  const uncertaintyReasons = ('uncertainty_reasons' in requirement ? requirement.uncertainty_reasons : []) ?? []
  const claims = ('claims' in requirement ? requirement.claims : []) ?? []

  return (
    <article className="requirement-card">
      <div className="requirement-header">
        <strong>{requirement.requirement_id}</strong>
        <div className="pill-row">
          <span className={`status-pill ${statusClass(requirement.review_status ?? 'candidate')}`}>{humanizeStatus(requirement.review_status ?? 'candidate')}</span>
          {finalLabel && <span className={`status-pill ${statusClass(finalLabel)}`}>{humanizeStatus(finalLabel)}</span>}
          {requirement.ui_evaluability && <span className={`status-pill ${statusClass(requirement.ui_evaluability)}`}>{humanizeStatus(requirement.ui_evaluability)}</span>}
        </div>
      </div>
      <p>{requirement.text}</p>
      <RequirementMeta requirement={requirement} onJumpToStep={onJumpToStep} />
      {intendedLabel && (
        <p className="editor-hint">
          Intended label only: <strong>{humanizeStatus(intendedLabel)}</strong>. This is a generation target, not the final gold label.
        </p>
      )}
      {uncertaintyReasons.length > 0 && (
        <p className="inline-note">Uncertainty: {uncertaintyReasons.map(humanizeStatus).join(', ')}</p>
      )}
      {claims.length > 0 && (
        <div className="claim-summary">
          {claims.slice(0, 3).map((claim, index) => (
            <div key={`${requirement.requirement_id}-claim-${index}`} className="claim-summary-row">
              {claim.status && <span className={`status-pill ${statusClass(claim.status)}`}>{humanizeStatus(claim.status)}</span>}
              <span>{claim.claim_text ?? claim.claim}</span>
            </div>
          ))}
          {claims.length > 3 && <span className="mini-label">{claims.length - 3} more claims</span>}
        </div>
      )}
      {actions}
    </article>
  )
}

function RequirementMeta({requirement, onJumpToStep}: {requirement: RequirementLike; onJumpToStep: (stepIndex: number) => void}) {
  const evidenceSteps = 'evidence_steps' in requirement ? requirement.evidence_steps : undefined

  return (
    <div className="meta-block">
      <span>Scope: {requirement.scope}</span>
      <span>Steps: <StepChipList stepIndices={requirement.step_indices} onJumpToStep={onJumpToStep} /></span>
      <span>Tags: {requirement.tags.join(', ') || 'none'}</span>
      {requirement.visible_subtype && <span>Visible subtype: {requirement.visible_subtype}</span>}
      {evidenceSteps && evidenceSteps.length > 0 && (
        <span>Evidence steps: <StepChipList stepIndices={evidenceSteps} onJumpToStep={onJumpToStep} /></span>
      )}
    </div>
  )
}

function StepChipList({stepIndices, onJumpToStep}: {stepIndices: number[]; onJumpToStep: (stepIndex: number) => void}) {
  if (stepIndices.length === 0) {
    return <span>none</span>
  }

  return (
    <span className="chip-row inline-chips">
      {stepIndices.map((stepIndex) => (
        <button key={stepIndex} className="step-chip inline" onClick={() => onJumpToStep(stepIndex)}>
          {stepIndex}
        </button>
      ))}
    </span>
  )
}

function RequirementEditorModal({
  mode,
  requirement,
  availableSteps,
  defaultAnnotatedBy,
  onClose,
  onSave,
  onDelete,
}: {
  mode: EditorMode
  requirement: RequirementLike
  availableSteps: FlowStep[]
  defaultAnnotatedBy: string
  onClose: () => void
  onSave: (
    action: 'review' | 'promote' | 'save_verification_gold',
    payload: RequirementPayload | VerificationGoldPayload,
    openNext?: boolean,
  ) => void
  onDelete: (requirement: RequirementLike) => void
}) {
  const isVerificationGold = mode === 'verification_gold'
  const verificationItem = isVerificationGold ? (requirement as VerificationGoldItem) : null
  const editableVerification = isVerificationGold || mode === 'candidate'
  const availableStepIndices = availableSteps.map((step) => step.step_index)
  const [rephrasingClaimIndex, setRephrasingClaimIndex] = useState<number | null>(null)
  const [rephrasingAllClaims, setRephrasingAllClaims] = useState<boolean>(false)
  const [form, setForm] = useState<RequirementFormState>(() => ({
    text: requirement.text,
    stepIndices: [...requirement.step_indices],
    tags: requirement.tags.join(', '),
    annotationNotes: requirement.annotation_notes ?? requirement.rationale ?? '',
    annotatedBy: requirement.annotated_by ?? defaultAnnotatedBy,
    reviewStatus: isVerificationGold ? 'accepted' : requirement.review_status ?? 'needs_review',
    verificationLabel: verificationItem?.verification_label ?? requirement.verification_label ?? '',
    uiEvaluability: verificationItem?.ui_evaluability ?? requirement.ui_evaluability ?? '',
    uncertaintyReasons: [...(verificationItem?.uncertainty_reasons ?? requirement.uncertainty_reasons ?? [])],
    evidenceSteps: [...(verificationItem?.evidence_steps ?? requirement.evidence_steps ?? requirement.step_indices)],
    evidenceNote: verificationItem?.evidence_note ?? requirement.evidence_note ?? '',
    rationale: verificationItem?.rationale ?? requirement.rationale ?? '',
    claims: (verificationItem?.claims ?? requirement.claims ?? []).map(toClaimFormState),
  }))

  function toggleStep(stepIndex: number, field: 'stepIndices' | 'evidenceSteps') {
    setForm((current) => {
      const nextSteps = current[field].includes(stepIndex)
        ? current[field].filter((item) => item !== stepIndex)
        : [...current[field], stepIndex].sort((a, b) => a - b)
      const nextForm = {
        ...current,
        [field]: nextSteps,
      }
      if (field !== 'evidenceSteps') {
        return nextForm
      }

      const allowed = new Set(nextSteps)
      return {
        ...nextForm,
        stepIndices: nextSteps,
        claims: current.claims.map((claim) => ({
          ...claim,
          evidenceSteps: claim.evidenceSteps.filter((claimStep) => allowed.has(claimStep)),
          evidenceUnit: claim.evidenceUnit && allowed.has(claim.evidenceUnit.step_index) ? claim.evidenceUnit : null,
        })),
      }
    })
  }

  function toggleClaimEvidenceStep(index: number, stepIndex: number) {
    setForm((current) => ({
      ...current,
      claims: current.claims.map((claim, claimIndex) => {
        if (claimIndex !== index) {
          return claim
        }
        const selected = claim.evidenceSteps.includes(stepIndex)
        const nextEvidenceSteps = selected
          ? claim.evidenceSteps.filter((claimStep) => claimStep !== stepIndex)
          : [...claim.evidenceSteps, stepIndex].sort((a, b) => a - b)
        return {
          ...claim,
          evidenceSteps: nextEvidenceSteps,
          evidenceUnit: selected && claim.evidenceUnit?.step_index === stepIndex ? null : claim.evidenceUnit,
        }
      }),
    }))
  }

  function toggleUncertaintyReason(reason: string) {
    setForm((current) => ({
      ...current,
      uncertaintyReasons: current.uncertaintyReasons.includes(reason)
        ? current.uncertaintyReasons.filter((item) => item !== reason)
        : [...current.uncertaintyReasons, reason],
    }))
  }

  function updateClaim(index: number, patch: Partial<ClaimFormState>) {
    setForm((current) => ({
      ...current,
      claims: current.claims.map((claim, claimIndex) => (claimIndex === index ? {...claim, ...patch} : claim)),
    }))
  }

  function addClaim() {
    setForm((current) => ({
      ...current,
      claims: [...current.claims, emptyClaimFormState()],
    }))
  }

  function removeClaim(index: number) {
    setForm((current) => ({
      ...current,
      claims: current.claims.filter((_, claimIndex) => claimIndex !== index),
    }))
  }

  async function rephraseClaim(index: number) {
    const claim = form.claims[index]
    if (!claim) {
      return
    }
    const feedback = window.prompt(
      'What is wrong with this claim, or what should the new claim include?\n\nExample: make it observable, focus on the visible selected store, avoid backend persistence.',
      '',
    )
    if (feedback === null) {
      return
    }
    const guidance = feedback.trim()
    if (!guidance) {
      return
    }
    setRephrasingClaimIndex(index)
    try {
      const response = await api.rephraseClaim({
        requirement_text: form.text,
        claim_text: claim.claim,
        feedback: guidance,
        claim_status: claim.status,
        claim_type: claim.claimType,
        importance: claim.importance,
      })
      const nextClaim = sentenceCase(stripRequirementBoilerplate(response.claim_text))
      if (nextClaim) {
        updateClaim(index, {claim: nextClaim})
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to rephrase claim')
    } finally {
      setRephrasingClaimIndex(null)
    }
  }

  async function rephraseAllClaims() {
    const requirementText = form.text.trim()
    if (!requirementText || rephrasingAllClaims) {
      return
    }
    setRephrasingAllClaims(true)
    try {
      const response = await api.decomposeClaims({
        requirement_text: requirementText,
        max_claims: 4,
      })
      const nextClaims = response.claims.map((claim, index) => {
        const existing = form.claims[index] ?? form.claims[form.claims.length - 1] ?? emptyClaimFormState()
        return {
          ...existing,
          claimId: '',
          claim: sentenceCase(stripRequirementBoilerplate(claim.claim_text ?? claim.claim)),
          claimType: claim.claim_type ?? existing.claimType,
          importance: existing.importance || claim.importance || 'CORE',
        }
      }).filter((claim) => claim.claim)
      if (nextClaims.length > 0) {
        setForm((current) => ({
          ...current,
          claims: nextClaims,
        }))
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Failed to rephrase all claims')
    } finally {
      setRephrasingAllClaims(false)
    }
  }

  const candidatePayload: RequirementPayload = {
    edited_text: form.text.trim(),
    edited_step_indices: form.evidenceSteps,
    edited_tags: parseTags(form.tags),
    annotation_notes: form.annotationNotes.trim() || undefined,
    annotated_by: form.annotatedBy.trim() || undefined,
    review_status: form.reviewStatus || undefined,
    verification_label: form.verificationLabel || undefined,
    ui_evaluability: form.uiEvaluability || undefined,
    uncertainty_reasons: form.uncertaintyReasons,
    evidence_steps: form.evidenceSteps,
    evidence_note: form.evidenceNote.trim() || undefined,
    rationale: form.rationale.trim() || undefined,
    claims: form.claims
      .filter((claim) => claim.claim.trim())
      .map(
        (claim): VerificationClaim => ({
          claim_id: claim.claimId || undefined,
          claim: claim.claim.trim(),
          claim_text: claim.claim.trim(),
          status: claim.status,
          claim_type: claim.claimType,
          importance: claim.importance,
          evidence_steps: claim.evidenceSteps,
          evidence_units: claimEvidenceUnitsForPayload(claim),
          uncertainty_reasons: claim.uncertaintyReasons,
          note: claim.note.trim() || undefined,
        }),
      ),
  }

  const verificationPayload: VerificationGoldPayload = {
    edited_text: form.text.trim(),
    edited_step_indices: form.evidenceSteps,
    edited_tags: parseTags(form.tags),
    annotation_notes: form.annotationNotes.trim() || undefined,
    annotated_by: form.annotatedBy.trim() || undefined,
    review_status: form.reviewStatus || undefined,
    verification_label: form.verificationLabel || undefined,
    ui_evaluability: form.uiEvaluability || undefined,
    uncertainty_reasons: form.uncertaintyReasons,
    evidence_steps: form.evidenceSteps,
    evidence_note: form.evidenceNote.trim() || undefined,
    rationale: form.rationale.trim() || undefined,
    claims: form.claims
      .filter((claim) => claim.claim.trim())
      .map(
        (claim): VerificationClaim => ({
          claim: claim.claim.trim(),
          claim_id: claim.claimId || undefined,
          claim_text: claim.claim.trim(),
          status: claim.status,
          claim_type: claim.claimType,
          importance: claim.importance,
          evidence_steps: claim.evidenceSteps,
          evidence_units: claimEvidenceUnitsForPayload(claim),
          uncertainty_reasons: claim.uncertaintyReasons,
          note: claim.note.trim() || undefined,
        }),
      ),
  }
  const acceptedCandidatePayload: RequirementPayload = {
    ...candidatePayload,
    review_status: 'accepted',
  }

  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
      if (event.key === 'Enter' && event.metaKey && !event.shiftKey) {
        event.preventDefault()
        if (mode === 'candidate') {
          onSave('promote', acceptedCandidatePayload)
        } else {
          onSave('save_verification_gold', verificationPayload)
        }
      }
      if (event.key === 'Enter' && event.metaKey && event.shiftKey) {
        event.preventDefault()
        if (mode === 'candidate') {
          onSave('promote', acceptedCandidatePayload, true)
        } else {
          onSave('save_verification_gold', verificationPayload, true)
        }
      }
      if (event.key === 'Backspace' && event.metaKey) {
        event.preventDefault()
        onDelete(requirement)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [acceptedCandidatePayload, candidatePayload, mode, onClose, onDelete, onSave, requirement, verificationPayload])

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header align-start">
          <div>
            <h3>{mode === 'candidate' ? 'Review candidate requirement' : 'Edit verification benchmark item'}</h3>
            <span>{requirement.requirement_id}</span>
          </div>
          <button className="secondary-button" onClick={onClose}>
            Close
          </button>
        </div>

        {'intended_label' in requirement && requirement.intended_label && (
          <section className="editor-callout">
            <strong>Intended label only</strong>
            <span>{humanizeStatus(requirement.intended_label)} is a contrastive generation target. Do not treat it as the final verification label.</span>
          </section>
        )}

        <div className="editor-grid">
          <label className={editableVerification ? 'sticky-requirement-text' : undefined}>
            Requirement text
            <textarea
              value={form.text}
              onChange={(event) => setForm({...form, text: event.target.value})}
              rows={editableVerification ? requirementTextRows(form.text) : 4}
            />
          </label>

          <label>
            Tags (comma separated)
            <input value={form.tags} onChange={(event) => setForm({...form, tags: event.target.value})} />
          </label>

          <label>
            Annotated by
            <input value={form.annotatedBy} onChange={(event) => setForm({...form, annotatedBy: event.target.value})} />
          </label>

          <label>
            Notes
            <textarea value={form.annotationNotes} onChange={(event) => setForm({...form, annotationNotes: event.target.value})} rows={3} />
          </label>

          {editableVerification && (
            <>
              <fieldset className="step-picker">
                <legend>Evidence steps</legend>
                <div className="chip-row">
                  {availableStepIndices.map((stepIndex) => {
                    const selected = form.evidenceSteps.includes(stepIndex)
                    return (
                      <button
                        type="button"
                        key={stepIndex}
                        className={selected ? 'step-chip selected' : 'step-chip'}
                        onClick={() => toggleStep(stepIndex, 'evidenceSteps')}
                      >
                        Step {stepIndex}
                      </button>
                    )
                  })}
                </div>
              </fieldset>

              <section className="claims-editor">
                <div className="panel-header">
                  <div>
                    <h4>Atomic claim evidence</h4>
                    <p className="helper-text">
                      Claims are atomic statements inside the requirement. Claim status explains how the screenshots support or fail to support each statement. The final verification label is assigned for the requirement as a whole.
                    </p>
                  </div>
                  <button type="button" className="secondary-button" onClick={addClaim}>
                    Add claim
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => void rephraseAllClaims()}
                    disabled={rephrasingAllClaims || rephrasingClaimIndex !== null}
                  >
                    {rephrasingAllClaims ? 'Rephrasing all...' : 'Rephrase all claims'}
                  </button>
                </div>
                {form.claims.length === 0 && <p className="empty-text">No claim rows yet.</p>}
                {form.claims.map((claim, index) => (
                  <div key={`claim-${index}`} className="claim-editor-row">
                    <label className="claim-main">
                      Claim
                      <textarea value={claim.claim} onChange={(event) => updateClaim(index, {claim: event.target.value})} rows={2} />
                    </label>
                    <label className="claim-status-field">
                      Status
                      <select value={claim.status} onChange={(event) => updateClaim(index, {status: event.target.value})}>
                        {CLAIM_STATUS_OPTIONS.map((status) => (
                          <option key={status} value={status}>
                            {humanizeStatus(status)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <fieldset className="claim-evidence-picker">
                      <legend>Evidence steps</legend>
                      <div className="chip-row">
                        {form.evidenceSteps.length > 0 ? (
                          form.evidenceSteps.map((stepIndex) => {
                            const selected = claim.evidenceSteps.includes(stepIndex)
                            return (
                              <button
                                type="button"
                                key={stepIndex}
                                className={selected ? 'step-chip inline selected' : 'step-chip inline'}
                                onClick={() => toggleClaimEvidenceStep(index, stepIndex)}
                              >
                                {stepIndex}
                              </button>
                            )
                          })
                        ) : (
                          <span className="empty-text">Select top-level evidence steps first.</span>
                        )}
                      </div>
                      {claim.evidenceSteps.length === 0 && ['SUPPORTED', 'SUPPORTED_WITH_CAVEAT', 'CONTRADICTED'].includes(claim.status) && (
                        <span className="mini-label">Supported or contradicted claims normally need evidence steps.</span>
                      )}
                    </fieldset>
                    <label className="claim-note">
                      Note
                      <input value={claim.note} onChange={(event) => updateClaim(index, {note: event.target.value})} />
                    </label>
                    <div className="claim-advanced-row">
                      <label>
                        Claim type
                        <select value={claim.claimType} onChange={(event) => updateClaim(index, {claimType: event.target.value})}>
                          {CLAIM_TYPE_OPTIONS.map((claimType) => (
                            <option key={claimType} value={claimType}>
                              {humanizeStatus(claimType)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Importance
                        <select value={claim.importance} onChange={(event) => updateClaim(index, {importance: event.target.value})}>
                          {CLAIM_IMPORTANCE_OPTIONS.map((importance) => (
                            <option key={importance} value={importance}>
                              {humanizeStatus(importance)}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <div className="claim-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={(event) => {
                          event.preventDefault()
                          event.stopPropagation()
                          void rephraseClaim(index)
                        }}
                        disabled={rephrasingClaimIndex !== null}
                      >
                        {rephrasingClaimIndex === index ? 'Rephrasing...' : 'Rephrase claim'}
                      </button>
                      <button type="button" className="danger-button" onClick={() => removeClaim(index)}>
                        Remove claim
                      </button>
                    </div>
                  </div>
                ))}
              </section>

              <section className="final-decision-section">
                <div>
                  <h4>Final verification decision</h4>
                  <p className="helper-text">Verification label is the draft benchmark label for candidate review and the final benchmark label for verification gold. UI evaluability is a separate axis. Uncertainty reasons explain why the item is not fully supported or why the decision is uncertain.</p>
                </div>

                <div className="editor-two-col">
                  <label>
                    Final verification label
                    <select value={form.verificationLabel} onChange={(event) => setForm({...form, verificationLabel: event.target.value})}>
                      <option value="">Select label</option>
                      {VERIFICATION_LABELS.map((label) => (
                        <option key={label} value={label}>
                          {humanizeStatus(label)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label>
                    UI evaluability
                    <select value={form.uiEvaluability} onChange={(event) => setForm({...form, uiEvaluability: event.target.value})}>
                      <option value="">Select axis label</option>
                      {UI_EVALUABILITY_OPTIONS.map((label) => (
                        <option key={label} value={label}>
                          {humanizeStatus(label)}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <fieldset className="step-picker uncertainty-picker">
                  <legend>Uncertainty reasons</legend>
                  <div className="checkbox-grid">
                    {UNCERTAINTY_REASON_OPTIONS.map((reason) => (
                      <label key={reason} className="checkbox-row">
                        <input
                          type="checkbox"
                          checked={form.uncertaintyReasons.includes(reason)}
                          onChange={() => toggleUncertaintyReason(reason)}
                        />
                        <span>{humanizeStatus(reason)}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <div className="editor-two-col">
                  <label>
                    Evidence note
                    <textarea value={form.evidenceNote} onChange={(event) => setForm({...form, evidenceNote: event.target.value})} rows={3} />
                  </label>

                  <label>
                    Rationale
                    <textarea value={form.rationale} onChange={(event) => setForm({...form, rationale: event.target.value})} rows={3} />
                  </label>
                </div>

                <label>
                  Review status
                  <select value={form.reviewStatus} onChange={(event) => setForm({...form, reviewStatus: event.target.value})}>
                    {REVIEW_STATUS_OPTIONS.map((label) => (
                      <option key={label} value={label}>
                        {humanizeStatus(label)}
                      </option>
                    ))}
                  </select>
                </label>
              </section>
            </>
          )}
        </div>

        <div className="button-row wrap">
          {mode === 'candidate' ? (
            <>
              <button type="button" className="secondary-button" onClick={() => onSave('review', candidatePayload)}>
                Save as needs review
              </button>
              <button type="button" className="danger-button" onClick={() => onDelete(requirement)}>
                Delete bad requirement
              </button>
              <button type="button" onClick={() => onSave('promote', acceptedCandidatePayload)}>
                Promote to gold
              </button>
            </>
          ) : (
            <>
              <button type="button" className="danger-button" onClick={() => onDelete(requirement)}>
                Delete bad requirement
              </button>
              <button type="button" onClick={() => onSave('save_verification_gold', verificationPayload)}>
                Save verification item
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function ImageLightbox({step, onClose}: {step: FlowStep; onClose: () => void}) {
  return (
    <div className="modal-backdrop lightbox-backdrop" onClick={onClose}>
      <div className="lightbox-card" onClick={(event) => event.stopPropagation()}>
        <div className="panel-header align-start">
          <div>
            <h3>Step {step.step_index}</h3>
            <span>{step.image_name}</span>
          </div>
          <div className="button-row wrap">
            <a className="link-button" href={resolveAssetUrl(step.original_image_url ?? step.image_url)} target="_blank" rel="noreferrer">
              Open image in new tab
            </a>
            <button type="button" className="secondary-button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <img className="lightbox-image" src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`} />
      </div>
    </div>
  )
}

function EvidenceBoxPreview({
  step,
  bbox,
  label,
  bboxMetadata = null,
  legacyVariant = 'display',
}: {
  step: FlowStep | null
  bbox: BoundingBox | null
  label: string
  bboxMetadata?: BoundingBoxMetadata | null
  legacyVariant?: 'display' | 'preview'
}) {
  if (!step || !bbox) {
    return null
  }
  const image = selectBoxImage(step, bboxMetadata, legacyVariant)
  return (
    <div className="evidence-box-preview">
      <span className="mini-label">{label}</span>
      <div className="bbox-canvas preview">
        <img src={resolveAssetUrl(image.url)} alt={`Step ${step.step_index}`} draggable={false} />
        <BoundingBoxOverlay bbox={bbox} imageWidth={image.width} imageHeight={image.height} />
      </div>
    </div>
  )
}

function EvidenceBoxesPreview({
  step,
  regions,
  label,
  legacyVariant = 'display',
}: {
  step: FlowStep | null
  regions: Array<{bbox: BoundingBox; bboxMetadata: BoundingBoxMetadata | null}>
  label: string
  legacyVariant?: 'display' | 'preview'
}) {
  if (!step || regions.length === 0) {
    return null
  }
  const image = selectBoxImage(step, regions[0].bboxMetadata, legacyVariant)
  return (
    <div className="evidence-box-preview">
      <span className="mini-label">{label}</span>
      <div className="bbox-canvas preview">
        <img src={resolveAssetUrl(image.url)} alt={`Step ${step.step_index}`} draggable={false} />
        {regions.map((region, index) => (
          <BoundingBoxOverlay
            key={`${index}-${region.bbox.x1}-${region.bbox.y1}-${region.bbox.x2}-${region.bbox.y2}`}
            bbox={scaleBoxForPreviewImage(region.bbox, region.bboxMetadata, image.width, image.height)}
            imageWidth={image.width}
            imageHeight={image.height}
          />
        ))}
      </div>
    </div>
  )
}

function scaleBoxForPreviewImage(
  bbox: BoundingBox,
  metadata: BoundingBoxMetadata | null,
  targetWidth?: number | null,
  targetHeight?: number | null,
): BoundingBox {
  const sourceWidth = metadata?.image_width
  const sourceHeight = metadata?.image_height
  if (!sourceWidth || !sourceHeight || !targetWidth || !targetHeight || (sourceWidth === targetWidth && sourceHeight === targetHeight)) {
    return bbox
  }
  return {
    x1: bbox.x1 * targetWidth / sourceWidth,
    y1: bbox.y1 * targetHeight / sourceHeight,
    x2: bbox.x2 * targetWidth / sourceWidth,
    y2: bbox.y2 * targetHeight / sourceHeight,
  }
}

function selectBoxImage(
  step: FlowStep,
  metadata: BoundingBoxMetadata | null,
  legacyVariant: 'display' | 'preview' = 'display',
): {url: string; width?: number | null; height?: number | null} {
  const metaWidth = metadata?.image_width
  const metaHeight = metadata?.image_height
  const displayMatches = sameImageSize(metaWidth, metaHeight, step.image_width, step.image_height)
  const previewMatches = sameImageSize(metaWidth, metaHeight, step.preview_image_width, step.preview_image_height)

  if (displayMatches) {
    return {url: step.image_url, width: step.image_width, height: step.image_height}
  }
  if (previewMatches && step.preview_image_url) {
    return {url: step.preview_image_url, width: step.preview_image_width, height: step.preview_image_height}
  }

  const metaPath = metadata?.image_path ?? ''
  if (metaPath && pathLooksLikeAsset(metaPath, step.image_url)) {
    return {url: step.image_url, width: step.image_width, height: step.image_height}
  }
  if (metaPath && step.preview_image_url && pathLooksLikeAsset(metaPath, step.preview_image_url)) {
    return {url: step.preview_image_url, width: step.preview_image_width, height: step.preview_image_height}
  }

  if (legacyVariant === 'preview' && step.preview_image_url) {
    return {url: step.preview_image_url, width: step.preview_image_width, height: step.preview_image_height}
  }
  return {url: step.image_url, width: step.image_width, height: step.image_height}
}

function sameImageSize(
  leftWidth?: number | null,
  leftHeight?: number | null,
  rightWidth?: number | null,
  rightHeight?: number | null,
): boolean {
  return Boolean(leftWidth && leftHeight && rightWidth && rightHeight && leftWidth === rightWidth && leftHeight === rightHeight)
}

function pathLooksLikeAsset(path: string, assetUrl: string): boolean {
  const normalizedPath = path.replace(/\\/g, '/')
  const normalizedAsset = assetUrl.replace(/\\/g, '/')
  return normalizedPath.endsWith(normalizedAsset) || normalizedAsset.endsWith(normalizedPath) || normalizedPath.endsWith(normalizedAsset.split('/static/').pop() ?? normalizedAsset)
}

function BoundingBoxOverlay({bbox, imageWidth, imageHeight}: {bbox: BoundingBox; imageWidth?: number | null; imageHeight?: number | null}) {
  const width = imageWidth && imageWidth > 0 ? imageWidth : Math.max(bbox.x2, 1)
  const height = imageHeight && imageHeight > 0 ? imageHeight : Math.max(bbox.y2, 1)
  const left = (bbox.x1 / width) * 100
  const top = (bbox.y1 / height) * 100
  const boxWidth = ((bbox.x2 - bbox.x1) / width) * 100
  const boxHeight = ((bbox.y2 - bbox.y1) / height) * 100
  return (
    <div
      className="bbox-overlay"
      style={{
        left: `${left}%`,
        top: `${top}%`,
        width: `${boxWidth}%`,
        height: `${boxHeight}%`,
      }}
    />
  )
}


function orderReviewItemsFirst<T extends {review_status?: string; requirement_id: string}>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const aNeedsReview = a.review_status === 'needs_review'
    const bNeedsReview = b.review_status === 'needs_review'
    if (aNeedsReview !== bNeedsReview) {
      return aNeedsReview ? -1 : 1
    }
    return a.requirement_id.localeCompare(b.requirement_id, undefined, {numeric: true})
  })
}

function requirementTextRows(text: string): number {
  const explicitLines = text.split('\n').length
  const wrappedLines = Math.ceil(text.length / 110)
  return Math.min(5, Math.max(1, explicitLines, wrappedLines))
}

function stripRequirementBoilerplate(value: string): string {
  return value
    .replace(/^the system shall offer\b/i, 'The system offers')
    .replace(/^the system shall provide\b/i, 'The system provides')
    .replace(/^the system shall present\b/i, 'The system presents')
    .replace(/^the system shall show\b/i, 'The system shows')
    .replace(/^the system shall allow\b/i, 'The system allows')
    .replace(/^the system shall support\b/i, 'The system supports')
    .replace(/^the system shall collect\b/i, 'The system collects')
    .replace(/^the flow shall offer\b/i, 'The flow offers')
    .replace(/^the flow shall provide\b/i, 'The flow provides')
    .replace(/^the flow shall present\b/i, 'The flow presents')
    .replace(/^the flow shall show\b/i, 'The flow shows')
    .replace(/^the flow shall allow\b/i, 'The flow allows')
    .replace(/^the flow shall support\b/i, 'The flow supports')
    .replace(/^the flow shall collect\b/i, 'The flow collects')
    .replace(/^users? can\s+/i, 'The user can ')
}

function sentenceCase(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }
  const capitalized = trimmed.charAt(0).toUpperCase() + trimmed.slice(1)
  return /[.!?]$/.test(capitalized) ? capitalized : `${capitalized}.`
}

function toClaimFormState(claim: VerificationClaim): ClaimFormState {
  const regionUnit = firstRegionEvidenceUnit(claim.evidence_units)
  const evidenceSteps = [...(claim.evidence_steps ?? [])]
  if (regionUnit && !evidenceSteps.includes(regionUnit.step_index)) {
    evidenceSteps.push(regionUnit.step_index)
    evidenceSteps.sort((a, b) => a - b)
  }
  return {
    claimId: claim.claim_id ?? '',
    claim: claim.claim_text ?? claim.claim,
    status: claim.status,
    claimType: claim.claim_type ?? 'OBSERVABLE',
    importance: claim.importance ?? 'CORE',
    evidenceSteps,
    evidenceUnit: regionUnit,
    note: claim.note ?? '',
    uncertaintyReasons: [...(claim.uncertainty_reasons ?? [])],
  }
}

function emptyClaimFormState(): ClaimFormState {
  return {
    claimId: '',
    claim: '',
    status: 'SUPPORTED',
    claimType: 'OBSERVABLE',
    importance: 'CORE',
    evidenceSteps: [],
    evidenceUnit: null,
    note: '',
    uncertaintyReasons: [],
  }
}

function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result ?? '')
      resolve(result.includes(',') ? result.split(',', 2)[1] : result)
    }
    reader.onerror = () => reject(reader.error ?? new Error(`Could not read ${file.name}`))
    reader.readAsDataURL(file)
  })
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function humanizeStatus(value: string | null | undefined): string {
  if (!value) {
    return 'Unknown'
  }
  const lowered = value.replace(/_/g, ' ').toLowerCase()
  return lowered.charAt(0).toUpperCase() + lowered.slice(1)
}

function statusClass(value: string | null | undefined): string {
  if (!value) {
    return 'unknown'
  }
  return value.trim().toLowerCase()
}

export default App
