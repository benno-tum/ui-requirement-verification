import {useEffect, useMemo, useState, type ReactNode} from 'react'
import {
  ApiError,
  api,
  resolveAssetUrl,
  type BoundingBox,
  type BoundingBoxMetadata,
  type EvidenceUnit,
  type PipelineVerificationRun,
  type PipelineRunJob,
  type PipelineRunSummary,
  type StartPipelineRunPayload,
  type FlowStep,
  type FlowSummary,
  type HarvestedRequirement,
  type Requirement,
  type RequirementPayload,
  type VerificationClaim,
  type VerificationGoldItem,
  type VerificationGoldPayload,
} from './api'

type LoadState = 'idle' | 'loading' | 'error'
type ViewMode = 'single' | 'multi' | 'overview' | 'harvested' | 'verification'
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
  {id: 'single', label: 'Single-screen review'},
  {id: 'multi', label: 'Multi-screen review'},
  {id: 'overview', label: 'Overview'},
  {id: 'harvested', label: 'Harvested'},
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
  {id: 'needs_review', label: 'Needs review'},
  {id: 'evidence_no_overlap', label: 'No evidence overlap'},
  {id: 'over_fulfilled', label: 'Over-fulfilled'},
  {id: 'should_abstain', label: 'Should abstain'},
  {id: 'under_called', label: 'Under-called'},
  {id: 'boundary', label: 'Boundary'},
  {id: 'late_state', label: 'Late state'},
  {id: 'universal_or_hidden', label: 'Universal/hidden'},
  {id: 'label_mismatch', label: 'Any label mismatch'},
]

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([])
  const [flowsState, setFlowsState] = useState<LoadState>('idle')
  const [selectedFlowId, setSelectedFlowId] = useState<string>('')
  const [selectedFlow, setSelectedFlow] = useState<FlowSummary | null>(null)
  const [steps, setSteps] = useState<FlowStep[]>([])
  const [harvested, setHarvested] = useState<HarvestedRequirement[]>([])
  const [candidates, setCandidates] = useState<Requirement[]>([])
  const [verificationGold, setVerificationGold] = useState<VerificationGoldItem[]>([])
  const [pipelineRun, setPipelineRun] = useState<PipelineVerificationRun | null>(null)
  const [detailsState, setDetailsState] = useState<LoadState>('idle')
  const [message, setMessage] = useState<string>('')
  const [annotatedBy, setAnnotatedBy] = useState<string>('benno')
  const [annotationNotes, setAnnotationNotes] = useState<string>('')
  const [maxImages, setMaxImages] = useState<number>(4)
  const [harvestModel, setHarvestModel] = useState<string>('gemini-2.5-flash')
  const [harvestTemperature, setHarvestTemperature] = useState<number>(0.7)
  const [harvestImageMaxSide, setHarvestImageMaxSide] = useState<number>(1280)
  const [viewMode, setViewMode] = useState<ViewMode>('single')
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
      const data = await api.listFlows()
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
    setHarvested([])
    setCandidates([])
    setVerificationGold([])
    setPipelineRun(null)

    try {
      const flow = await api.getFlow(flowId)
      setSelectedFlow(flow)

      const [stepsResult, harvestedResult, candidatesResult, verificationGoldResult, pipelineRunResult] = await Promise.allSettled([
        api.getSteps(flowId),
        api.listHarvested(flowId),
        api.listCandidates(flowId),
        api.listVerificationGold(flowId),
        api.getLatestPipelineVerification(flowId),
      ])

      if (stepsResult.status === 'fulfilled') {
        setSteps(stepsResult.value)
      }
      if (harvestedResult.status === 'fulfilled') {
        setHarvested(harvestedResult.value)
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
        const data = await api.listFlows()
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
        await api.acceptCandidate(selectedFlowId, requirement.requirement_id, {
          annotation_notes: annotationNotes || undefined,
          annotated_by: annotatedBy || undefined,
        })
      } else if (action === 'reject') {
        await api.rejectCandidate(selectedFlowId, requirement.requirement_id, {
          reason: annotationNotes || undefined,
          annotated_by: annotatedBy || undefined,
        })
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

  async function handleGenerateHarvestedRequirements() {
    if (!selectedFlowId) {
      return
    }
    setMessage('')
    try {
      const result = await api.generateHarvestedRequirements(selectedFlowId, {
        max_images: maxImages,
        image_max_side: harvestImageMaxSide,
        model_name: harvestModel,
        temperature: harvestTemperature,
      })
      await loadFlowDetails(selectedFlowId)
      setViewMode('harvested')
      setMessage(`Generated ${result.harvested_count} harvested requirements.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to generate harvested requirements')
    }
  }

  async function handleMaterializeCandidatesFromHarvested() {
    if (!selectedFlowId) {
      return
    }
    setMessage('')
    try {
      const result = await api.rebuildCandidatesFromHarvested(selectedFlowId)
      await loadFlowDetails(selectedFlowId)
      setViewMode('single')
      setMessage(`Rebuilt ${result.candidate_count} candidate requirements from harvested items.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to rebuild candidates from harvested requirements')
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
        annotation_notes: annotationNotes || undefined,
        annotated_by: annotatedBy || undefined,
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
  const isPureFlow = selectedFlow?.dataset === 'pure'

  const singleScreenCandidates = useMemo(
    () => activeCandidates.filter((candidate) => candidate.step_indices.length <= 1),
    [activeCandidates],
  )
  const multiScreenCandidates = useMemo(
    () => activeCandidates.filter((candidate) => candidate.step_indices.length > 1),
    [activeCandidates],
  )
  const singleScreenGold = useMemo(
    () => orderedVerificationGold.filter((item) => item.step_indices.length <= 1),
    [orderedVerificationGold],
  )
  const multiScreenGold = useMemo(
    () => orderedVerificationGold.filter((item) => item.step_indices.length > 1),
    [orderedVerificationGold],
  )

  const candidateGroupsByStep = useMemo(() => groupRequirementsBySingleStep(singleScreenCandidates), [singleScreenCandidates])
  const goldGroupsByStep = useMemo(() => groupRequirementsBySingleStep(singleScreenGold), [singleScreenGold])

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
          <div className="topbar-header">
            <div>
              <h2>{selectedFlow?.flow_id ?? 'Select a flow'}</h2>
              <p>{selectedFlow?.confirmed_task ?? 'No task loaded yet.'}</p>
            </div>
            <div className="dual-status-explainer">
              <strong>Dual axes</strong>
              <span>Verification label judges the shown outcome. UI evaluability judges whether screenshots can verify the claim at all.</span>
            </div>
          </div>

          <div className="toolbar-grid">
            <label>
              Annotated by
              <input value={annotatedBy} onChange={(event) => setAnnotatedBy(event.target.value)} placeholder="annotator" />
            </label>
            <label>
              Notes
              <input value={annotationNotes} onChange={(event) => setAnnotationNotes(event.target.value)} placeholder="optional note" />
            </label>
            <label>
              Max images
              <input type="number" min={1} value={maxImages} onChange={(event) => setMaxImages(Number(event.target.value) || 1)} />
            </label>
            <button className="secondary-button" onClick={openNextNeedsReviewItem} disabled={!selectedFlow}>
              Next needs review
            </button>
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

        {selectedFlow && viewMode === 'single' && (
          <SingleScreenReview
            steps={steps}
            highlightedStep={highlightedStep}
            candidatesByStep={candidateGroupsByStep}
            goldByStep={goldGroupsByStep}
            onOpenZoom={setZoomStep}
            onJumpToStep={jumpToStep}
            onPromote={(requirement) => void handleCandidateAction('accept', requirement)}
            onEditCandidate={(requirement) => setEditor({mode: 'candidate', requirement})}
            onReject={(requirement) => void handleCandidateAction('reject', requirement)}
            onEditGold={(requirement) => setEditor({mode: 'verification_gold', requirement})}
            unlinkedCandidates={singleScreenCandidates.filter((candidate) => candidate.step_indices.length === 0)}
            unlinkedGold={singleScreenGold.filter((item) => item.step_indices.length === 0)}
          />
        )}

        {selectedFlow && viewMode === 'multi' && (
          <MultiScreenReview
            steps={steps}
            candidates={multiScreenCandidates}
            gold={multiScreenGold}
            onJumpToStep={jumpToStep}
            onEditCandidate={(requirement) => setEditor({mode: 'candidate', requirement})}
            onPromote={(requirement) => void handleCandidateAction('accept', requirement)}
            onReject={(requirement) => void handleCandidateAction('reject', requirement)}
            onEditGold={(requirement) => setEditor({mode: 'verification_gold', requirement})}
          />
        )}

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

        {selectedFlow && viewMode === 'harvested' && (
          <HarvestedPanel
            harvested={harvested}
            harvestModel={harvestModel}
            harvestTemperature={harvestTemperature}
            harvestImageMaxSide={harvestImageMaxSide}
            supportsGeneration={!isPureFlow}
            onHarvestModelChange={setHarvestModel}
            onHarvestTemperatureChange={setHarvestTemperature}
            onHarvestImageMaxSideChange={setHarvestImageMaxSide}
            onJumpToStep={jumpToStep}
            onGenerate={() => void handleGenerateHarvestedRequirements()}
            onMaterialize={() => void handleMaterializeCandidatesFromHarvested()}
          />
        )}

        {selectedFlow && viewMode === 'verification' && (
          <VerificationRunPanel
            flowId={selectedFlow.flow_id}
            steps={steps}
            pipelineRun={pipelineRun}
            verificationGold={verificationGold}
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
          defaultAnnotatedBy={annotatedBy}
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

function SingleScreenReview({
  steps,
  highlightedStep,
  candidatesByStep,
  goldByStep,
  unlinkedCandidates,
  unlinkedGold,
  onOpenZoom,
  onJumpToStep,
  onPromote,
  onEditCandidate,
  onReject,
  onEditGold,
}: {
  steps: FlowStep[]
  highlightedStep: number | null
  candidatesByStep: Map<number, Requirement[]>
  goldByStep: Map<number, VerificationGoldItem[]>
  unlinkedCandidates: Requirement[]
  unlinkedGold: VerificationGoldItem[]
  onOpenZoom: (step: FlowStep) => void
  onJumpToStep: (stepIndex: number) => void
  onPromote: (requirement: Requirement) => void
  onEditCandidate: (requirement: Requirement) => void
  onReject: (requirement: Requirement) => void
  onEditGold: (requirement: VerificationGoldItem) => void
}) {
  return (
    <section className="stack-layout">
      <section className="card sticky-card">
        <div className="panel-header">
          <h3>Flow screens</h3>
          <span>Click a step to jump. Click an image to zoom.</span>
        </div>
        {steps.length > 0 ? (
          <div className="chip-row">
            {steps.map((step) => (
              <button key={step.step_index} className="step-chip" onClick={() => onJumpToStep(step.step_index)}>
                Step {step.step_index}
              </button>
            ))}
          </div>
        ) : (
          <p className="empty-text">No UI images were extracted for this flow. Requirements are still available below.</p>
        )}
      </section>

      {steps.length === 0 && (
        <section className="content-grid">
          <section className="card">
            <div className="panel-header">
              <h3>Pending candidate requirements</h3>
              <span>{unlinkedCandidates.length}</span>
            </div>
            <div className="requirement-list compact-list">
              {unlinkedCandidates.length > 0 ? (
                unlinkedCandidates.map((requirement) => (
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
                ))
              ) : (
                <p className="empty-text">No pending candidates.</p>
              )}
            </div>
          </section>

          <section className="card">
            <div className="panel-header">
              <h3>Verification benchmark items</h3>
              <span>{unlinkedGold.length}</span>
            </div>
            <div className="requirement-list compact-list">
              {unlinkedGold.length > 0 ? (
                unlinkedGold.map((requirement) => (
                  <RequirementCard
                    key={requirement.requirement_id}
                    requirement={requirement}
                    onJumpToStep={onJumpToStep}
                    actions={
                      <div className="button-row left wrap">
                        <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                          Edit verification labels
                        </button>
                      </div>
                    }
                  />
                ))
              ) : (
                <p className="empty-text">No verification benchmark items yet.</p>
              )}
            </div>
          </section>
        </section>
      )}

      {steps.map((step) => {
        const stepCandidates = candidatesByStep.get(step.step_index) ?? []
        const stepGold = goldByStep.get(step.step_index) ?? []
        return (
          <article
            key={step.step_index}
            id={`step-${step.step_index}`}
            className={highlightedStep === step.step_index ? 'card step-focus-card highlighted' : 'card step-focus-card'}
          >
            <div className="panel-header align-start">
              <div>
                <h3>Step {step.step_index}</h3>
                <span>{stepCandidates.length} pending single-screen candidates · {stepGold.length} verification items</span>
                {step.artifact_label && <span className="artifact-badge">{step.artifact_label}{step.artifact_page ? ` · page ${step.artifact_page}` : ''}</span>}
              </div>
              <button className="secondary-button" onClick={() => onOpenZoom(step)}>
                Open larger view
              </button>
            </div>

            <img
              className="step-image-large"
              src={resolveAssetUrl(step.image_url)}
              alt={`Step ${step.step_index}`}
              loading="lazy"
              onClick={() => onOpenZoom(step)}
            />

            <div className="step-linked-grid">
              <section className="linked-column">
                <div className="subsection-header">
                  <h4>Pending candidate requirements</h4>
                  <span>{stepCandidates.length}</span>
                </div>
                {stepCandidates.length > 0 ? (
                  <div className="requirement-list compact-list">
                    {stepCandidates.map((requirement) => (
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
                ) : (
                  <p className="empty-text">No pending single-screen candidates linked to this step.</p>
                )}
              </section>

              <section className="linked-column">
                <div className="subsection-header">
                  <h4>Verification benchmark items</h4>
                  <span>{stepGold.length}</span>
                </div>
                {stepGold.length > 0 ? (
                  <div className="requirement-list compact-list">
                    {stepGold.map((requirement) => (
                      <RequirementCard
                        key={requirement.requirement_id}
                        requirement={requirement}
                        onJumpToStep={onJumpToStep}
                        actions={
                          <div className="button-row left wrap">
                            <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                              Edit verification labels
                            </button>
                          </div>
                        }
                      />
                    ))}
                  </div>
                ) : (
                  <p className="empty-text">No verification benchmark item linked to this step yet.</p>
                )}
              </section>
            </div>
          </article>
        )
      })}
    </section>
  )
}

function MultiScreenReview({
  steps,
  candidates,
  gold,
  onJumpToStep,
  onEditCandidate,
  onPromote,
  onReject,
  onEditGold,
}: {
  steps: FlowStep[]
  candidates: Requirement[]
  gold: VerificationGoldItem[]
  onJumpToStep: (stepIndex: number) => void
  onEditCandidate: (requirement: Requirement) => void
  onPromote: (requirement: Requirement) => void
  onReject: (requirement: Requirement) => void
  onEditGold: (requirement: VerificationGoldItem) => void
}) {
  return (
    <section className="content-grid">
      <section className="card panel-wide">
        <div className="panel-header">
          <h3>Flow step navigator</h3>
          <span>{steps.length} screens</span>
        </div>
        <div className="chip-row">
          {steps.map((step) => (
            <button key={step.step_index} className="step-chip" onClick={() => onJumpToStep(step.step_index)}>
              Step {step.step_index}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Pending multi-screen candidates</h3>
          <span>{candidates.length}</span>
        </div>
        <div className="requirement-list compact-list">
          {candidates.length > 0 ? (
            candidates.map((requirement) => (
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
            ))
          ) : (
            <p className="empty-text">No pending multi-screen candidates.</p>
          )}
        </div>
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Verification benchmark items</h3>
          <span>{gold.length}</span>
        </div>
        <div className="requirement-list compact-list">
          {gold.length > 0 ? (
            gold.map((requirement) => (
              <RequirementCard
                key={requirement.requirement_id}
                requirement={requirement}
                onJumpToStep={onJumpToStep}
                actions={
                  <div className="button-row left wrap">
                    <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                      Edit verification labels
                    </button>
                  </div>
                }
              />
            ))
          ) : (
            <p className="empty-text">No multi-screen verification benchmark items yet.</p>
          )}
        </div>
      </section>
    </section>
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

function HarvestedPanel({
  harvested,
  harvestModel,
  harvestTemperature,
  harvestImageMaxSide,
  supportsGeneration,
  onHarvestModelChange,
  onHarvestTemperatureChange,
  onHarvestImageMaxSideChange,
  onJumpToStep,
  onGenerate,
  onMaterialize,
}: {
  harvested: HarvestedRequirement[]
  harvestModel: string
  harvestTemperature: number
  harvestImageMaxSide: number
  supportsGeneration: boolean
  onHarvestModelChange: (value: string) => void
  onHarvestTemperatureChange: (value: number) => void
  onHarvestImageMaxSideChange: (value: number) => void
  onJumpToStep: (stepIndex: number) => void
  onGenerate: () => void
  onMaterialize: () => void
}) {
  return (
    <section className="content-grid">
      <section className="card panel-wide">
        <div className="panel-header">
          <div>
            <h3>Harvested requirement hypotheses</h3>
            <span>{harvested.length} items</span>
          </div>
          {supportsGeneration ? (
            <div className="button-row wrap">
              <label>
                Harvest model
                <select value={harvestModel} onChange={(event) => onHarvestModelChange(event.target.value)}>
                  <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                  <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
                </select>
              </label>
              <label>
                Harvest temperature
                <input type="number" min={0} max={1} step={0.1} value={harvestTemperature} onChange={(event) => onHarvestTemperatureChange(Number(event.target.value))} />
              </label>
              <label>
                Harvest image max side
                <input type="number" min={512} max={2048} step={128} value={harvestImageMaxSide} onChange={(event) => onHarvestImageMaxSideChange(Number(event.target.value) || 1280)} />
              </label>
              <button onClick={onGenerate}>Generate harvested requirements</button>
              <button onClick={onMaterialize} disabled={harvested.length === 0}>
                Replace candidates from harvested
              </button>
            </div>
          ) : (
            <p className="inline-note">Requirement generation from screenshots is disabled for PURE flows. These candidates come from the PURE source document export.</p>
          )}
        </div>
        {supportsGeneration && <p className="inline-note">These are the broader hypotheses produced from the UI flow before candidate normalization.</p>}
        {harvested.length > 0 ? (
          <div className="requirement-list compact-list">
            {harvested.map((item) => (
              <article key={item.harvest_id} className="requirement-card">
                <div className="requirement-header">
                  <strong>{item.harvest_id}</strong>
                  <div className="pill-row">
                    <span className={`status-pill ${statusClass(item.ui_evaluability)}`}>{humanizeStatus(item.ui_evaluability)}</span>
                    <span className="status-pill">{item.visible_subtype}</span>
                    <span className="status-pill">{item.task_relevance}</span>
                  </div>
                </div>
                <p>{item.harvested_text}</p>
                <div className="meta-block">
                  <span>Type: {item.requirement_type}</span>
                  <span>Confidence: {item.confidence ?? 'n/a'}</span>
                  <span>Steps: <StepChipList stepIndices={item.step_indices} onJumpToStep={onJumpToStep} /></span>
                </div>
                {item.visible_core_candidate && <p className="inline-note">Visible-core rewrite suggestion: {item.visible_core_candidate}</p>}
                {item.non_evaluable_reason && item.non_evaluable_reason !== 'NONE' && <p className="inline-note">Limitation: {humanizeStatus(item.non_evaluable_reason)}</p>}
                {item.rationale && <p className="inline-note">Rationale: {item.rationale}</p>}
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-text">No harvested requirements available for this flow yet.</p>
        )}
      </section>
    </section>
  )
}

function VerificationRunPanel({
  flowId,
  steps,
  pipelineRun,
  verificationGold,
  onJumpToStep,
  onEditVerificationGold,
  onAcceptVerificationGold,
}: {
  flowId: string
  steps: FlowStep[]
  pipelineRun: PipelineVerificationRun | null
  verificationGold: VerificationGoldItem[]
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
  const [reviewCategoryId, setReviewCategoryId] = useState<ReviewCategoryId>('needs_review')
  const [runForm, setRunForm] = useState<StartPipelineRunPayload>({
    verifier: 'deterministic_rule_based',
    verifier_model: 'gemini-2.5-flash-lite',
    retriever: 'lexical',
    requirements_source: 'benchmark',
    top_k: 3,
    max_images: 6,
    max_gemini_api_calls: 0,
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
    : `data/annotations/requirements_gold/${flowId}/gold_requirements.json`
  const cliCommand = `PYTHONPATH=src:. python scripts/run_verification_pipeline.py --flow-dir data/processed/flows/mind2web/${flowId} --requirements ${requirementsPath} --requirements-source ${runForm.requirements_source} --out data/generated/${runForm.output_dir_name}/${flowId}.json --retriever lexical --verifier ${runForm.verifier === 'deterministic_rule_based' ? 'deterministic' : 'gemini-image'} --verifier-model ${runForm.verifier_model} --max-verifier-images ${runForm.max_images} --max-gemini-api-calls ${runForm.max_gemini_api_calls} --no-llm-claim-fallback`

  const metadata = activeRun?.metadata ?? {}
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
      if (row.review_status !== 'needs_review') {
        continue
      }
      counts.set('needs_review', (counts.get('needs_review') ?? 0) + 1)
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
        : row.review_status === 'needs_review' && row.category_ids.includes(reviewCategoryId),
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
            <div className="demo-table">
              <div className="demo-table-header">
                <span>Source</span>
                <span>Verifier</span>
                <span>Retriever</span>
                <span>Labels</span>
              </div>
              {runs.map((run) => (
                <button
                  key={run.run_id}
                  className="demo-table-row comparison-row-button"
                  onClick={() => void selectRun(run.run_id)}
                >
                  <span className="review-mini-stack">
                    <strong title={run.path}>{runLabel(run)}</strong>
                    <span title={run.path}>{run.source}</span>
                    {runHasBboxHint(run) && <span className="status-pill supported">Bbox evidence</span>}
                    <span>{formatTimestamp(run.timestamp)}</span>
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
          </>
        ) : (
          <p className="empty-text">No generated verification pipeline output exists for this flow yet.</p>
        )}
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Run pipeline</h3>
          <span>Starting a Gemini run is an explicit action and may consume API quota.</span>
        </div>
        <div className="toolbar-grid">
          <label>
            Verifier
            <select
              value={runForm.verifier}
              onChange={(event) => setRunForm({...runForm, verifier: event.target.value as StartPipelineRunPayload['verifier']})}
            >
              <option value="deterministic_rule_based">deterministic_rule_based</option>
              <option value="gemini-image">gemini-image</option>
            </select>
          </label>
          <label>
            Verifier model
            <input value={runForm.verifier_model} onChange={(event) => setRunForm({...runForm, verifier_model: event.target.value})} />
          </label>
          <label>
            Retriever
            <select value={runForm.retriever} onChange={() => setRunForm({...runForm, retriever: 'lexical'})}>
              <option value="lexical">lexical</option>
            </select>
          </label>
          <label>
            Requirements
            <select
              value={runForm.requirements_source}
              onChange={(event) => setRunForm({...runForm, requirements_source: event.target.value as StartPipelineRunPayload['requirements_source']})}
            >
              <option value="benchmark">verification benchmark</option>
              <option value="accepted">accepted requirements</option>
            </select>
          </label>
          <label>
            Output directory
            <input value={runForm.output_dir_name} onChange={(event) => setRunForm({...runForm, output_dir_name: event.target.value})} />
          </label>
          <label>
            Top-k
            <input type="number" min={1} max={20} value={runForm.top_k} onChange={(event) => setRunForm({...runForm, top_k: Number(event.target.value)})} />
          </label>
          <label>
            Max images
            <input type="number" min={1} max={20} value={runForm.max_images} onChange={(event) => setRunForm({...runForm, max_images: Number(event.target.value)})} />
          </label>
          <label>
            Max Gemini API calls
            <input
              type="number"
              min={-1}
              max={1000}
              value={runForm.max_gemini_api_calls}
              onChange={(event) => setRunForm({...runForm, max_gemini_api_calls: Number(event.target.value)})}
            />
          </label>
          <label>
            Use cache
            <select value={runForm.use_cache ? 'true' : 'false'} onChange={(event) => setRunForm({...runForm, use_cache: event.target.value === 'true'})}>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
        </div>
        <div className="button-row">
          <button onClick={() => void startRun()} disabled={runJob?.status === 'running'}>
            Run pipeline
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

      <section className="card">
        <div className="panel-header">
          <h3>Reviewed-label comparison</h3>
          <span>{filteredComparisonRows.length} shown. Review queues use open verification-gold items only.</span>
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
      </section>

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
                  Inspect manual vs pipeline
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
            <h3>Manual vs pipeline comparison</h3>
            <span>{result.requirement_id}</span>
          </div>
          <div className="button-row wrap">
            <button
              type="button"
              className="secondary-button"
              disabled={!onEditBenchmarkItem}
              title={onEditBenchmarkItem ? 'Edit current verification benchmark item' : 'Benchmark item is missing or changed since this run'}
              onClick={onEditBenchmarkItem}
            >
              Edit benchmark item
            </button>
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
          <div className="comparison-verdict-strip">
            <div>
              <span>Manual benchmark</span>
              <strong className={`status-pill ${statusClass(goldLabel)}`}>{humanizeStatus(goldLabel)}</strong>
            </div>
            <div>
              <span>Pipeline decision</span>
              <strong className={`status-pill ${statusClass(predictedLabel)}`}>{humanizeStatus(predictedLabel)}</strong>
            </div>
            <div>
              <span>Risk</span>
              <strong>{falseFulfillment ? 'False fulfillment' : labelMismatch ? 'Label mismatch' : 'Label aligned'}</strong>
            </div>
          </div>
        </section>

        <section className="comparison-section">
          <div className="panel-header">
            <h4>Final label and claim composition</h4>
            <span>The pipeline label is produced by the aggregation step, not by copying one claim.</span>
          </div>
          <div className="composition-grid">
            <article className="composition-card">
              <span className="mini-label">Manual final label</span>
              <strong className={`status-pill ${statusClass(goldLabel)}`}>{humanizeStatus(goldLabel)}</strong>
              <p>Claim labels: {formatDistribution(manualClaimDistribution)}</p>
              <p>Ambiguity: {formatReasons(gold?.uncertainty_reasons ?? [])}</p>
            </article>
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
          <ComparisonColumn
            title="Manual benchmark"
            label={goldLabel}
            uiEvaluability={gold?.ui_evaluability}
            uncertaintyReasons={gold?.uncertainty_reasons ?? []}
            evidenceSteps={goldEvidenceSteps}
            rationale={gold?.rationale}
            evidenceNote={gold?.evidence_note}
            onJumpToStep={onJumpToStep}
          />
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

        <section className="comparison-section">
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
        </section>

        <section className="comparison-section">
          <div className="panel-header">
            <div>
              <h4>Claim alignment</h4>
              <span>Manual claims are aligned to pipeline claims by token overlap.</span>
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
}: {
  alignment: ClaimAlignment
  steps: FlowStep[]
  onJumpToStep: (stepIndex: number) => void
}) {
  const goldClaim = alignment.goldClaim
  const predictedClaim = alignment.predictedClaim
  const statusMismatch = normalizeDisplayValue(goldClaim?.status) !== normalizeDisplayValue(predictedClaim?.status)
  const goldEvidenceUnit = firstRegionEvidenceUnit(goldClaim?.evidence_units)
  return (
    <article className={statusMismatch ? 'claim-alignment-row status-mismatch' : 'claim-alignment-row'}>
      <div className="alignment-score">
        <span>match</span>
        <strong>{alignment.score.toFixed(2)}</strong>
      </div>
      <div className="aligned-claim manual">
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
      </div>
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
              {predictedClaim.evidence.slice(0, 3).map((evidence) => {
                const bbox = normalizeBoundingBox(evidence.bbox)
                return (
                  <div key={`${predictedClaim.claim_id}-${evidence.step_index}`} className="evidence-snippet-group">
                    <button className="evidence-snippet" onClick={() => onJumpToStep(evidence.step_index)}>
                      <strong>Step {evidence.step_index}</strong>
                      <span>{truncateText(evidence.visible_observation, 260)}</span>
                    </button>
                    {bbox && (
                      <EvidenceBoxPreview
                        step={steps.find((step) => step.step_index === evidence.step_index) ?? null}
                        bbox={bbox}
                        label="Pipeline box"
                        bboxMetadata={metadataFromPipelineEvidence(evidence)}
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

function groupRequirementsBySingleStep<T extends {step_indices: number[]}>(requirements: T[]): Map<number, T[]> {
  const groups = new Map<number, T[]>()
  requirements.forEach((requirement) => {
    const stepIndex = requirement.step_indices[0]
    if (stepIndex === undefined) {
      return
    }
    const current = groups.get(stepIndex) ?? []
    current.push(requirement)
    groups.set(stepIndex, current)
  })
  return groups
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
