import {useEffect, useMemo, useState, type ReactNode} from 'react'
import {
  ApiError,
  api,
  resolveAssetUrl,
  type DemoVerificationRun,
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
type ViewMode = 'single' | 'multi' | 'overview' | 'harvested' | 'demo'
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
  note: string
  uncertaintyReasons: string[]
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
  {id: 'demo', label: 'Demo run'},
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
const CLAIM_STATUS_OPTIONS = ['SUPPORTED', 'CONTRADICTED', 'MISSING', 'HIDDEN', 'AMBIGUOUS', 'OUT_OF_SCOPE']
const CLAIM_TYPE_OPTIONS = ['OBSERVABLE', 'HIDDEN']
const CLAIM_IMPORTANCE_OPTIONS = ['CORE', 'SUPPORTING']

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([])
  const [flowsState, setFlowsState] = useState<LoadState>('idle')
  const [selectedFlowId, setSelectedFlowId] = useState<string>('')
  const [selectedFlow, setSelectedFlow] = useState<FlowSummary | null>(null)
  const [steps, setSteps] = useState<FlowStep[]>([])
  const [harvested, setHarvested] = useState<HarvestedRequirement[]>([])
  const [candidates, setCandidates] = useState<Requirement[]>([])
  const [verificationGold, setVerificationGold] = useState<VerificationGoldItem[]>([])
  const [demoRun, setDemoRun] = useState<DemoVerificationRun | null>(null)
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
    setDemoRun(null)

    try {
      const flow = await api.getFlow(flowId)
      setSelectedFlow(flow)

      const [stepsResult, harvestedResult, candidatesResult, verificationGoldResult, demoRunResult] = await Promise.allSettled([
        api.getSteps(flowId),
        api.listHarvested(flowId),
        api.listCandidates(flowId),
        api.listVerificationGold(flowId),
        api.getLatestDemoVerification(flowId),
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
      if (demoRunResult.status === 'fulfilled') {
        setDemoRun(demoRunResult.value)
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

  const activeCandidates = useMemo(
    () => candidates.filter((candidate) => candidate.review_status !== 'accepted' && candidate.review_status !== 'rejected'),
    [candidates],
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

        {selectedFlow && viewMode === 'demo' && (
          <DemoRunPanel
            demoRun={demoRun}
            onJumpToStep={jumpToStep}
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
          availableSteps={steps.map((step) => step.step_index)}
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
          <h3>Verification benchmark items</h3>
          <span>{gold.length}</span>
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

function DemoRunPanel({
  demoRun,
  onJumpToStep,
}: {
  demoRun: DemoVerificationRun | null
  onJumpToStep: (stepIndex: number) => void
}) {
  if (!demoRun) {
    return (
      <section className="card">
        <div className="panel-header">
          <h3>Demo run</h3>
          <span>No generated demo verification output exists for this flow yet.</span>
        </div>
        <p className="inline-note">Run the CLI command from the repository root, then refresh this page:</p>
        <pre className="code-block">PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id &lt;flow_id&gt;</pre>
      </section>
    )
  }

  const metadata = demoRun.metadata
  const labelDistribution = (metadata.label_distribution ?? {}) as Record<string, number>
  const claimStatusDistribution = (metadata.claim_status_distribution ?? {}) as Record<string, number>
  const referenceComparison = (metadata.reference_comparison ?? {}) as {
    summary?: Record<string, unknown>
    items?: Array<Record<string, unknown>>
  }
  const comparisonSummary = referenceComparison.summary ?? {}
  const comparisonRows = [...(referenceComparison.items ?? [])].sort((a, b) => {
    const aMatch = a.matches_reference === false ? 0 : 1
    const bMatch = b.matches_reference === false ? 0 : 1
    if (aMatch !== bMatch) {
      return aMatch - bMatch
    }
    return String(a.requirement_id ?? '').localeCompare(String(b.requirement_id ?? ''), undefined, {numeric: true})
  })

  return (
    <section className="stack-layout">
      <section className="card">
        <div className="panel-header">
          <h3>Demo verification run</h3>
          <span>{demoRun.flow_id}</span>
        </div>
        <div className="metric-grid">
          <Metric label="Requirements" value={String(metadata.requirements_count ?? demoRun.results.length)} />
          <Metric label="Claims" value={String(metadata.claim_count ?? demoRun.results.reduce((sum, result) => sum + result.claims.length, 0))} />
          <Metric label="Retriever" value={String(metadata.selected_retriever ?? metadata.retriever ?? 'unknown')} />
          <Metric label="Verifier" value={String(metadata.verifier ?? 'unknown')} />
          <Metric label="Reference matches" value={`${comparisonSummary.matches ?? 'n/a'} / ${comparisonSummary.compared_items ?? 'n/a'}`} />
          <Metric label="Reference accuracy" value={comparisonSummary.accuracy_on_matched_ids === undefined ? 'n/a' : String(comparisonSummary.accuracy_on_matched_ids)} />
        </div>
        <div className="meta-block">
          <span>Labels: {formatDistribution(labelDistribution)}</span>
          <span>Claim statuses: {formatDistribution(claimStatusDistribution)}</span>
          <span>Screen source mode: {String(metadata.screen_source_mode ?? 'current')}</span>
          <span>Raw HTML used: {String(metadata.raw_html_used ?? 'unknown')}</span>
          <span>Screenshot images used: {String(metadata.screenshot_images_used ?? 'unknown')}</span>
          <span>OCR: {String(((metadata.ocr ?? {}) as Record<string, unknown>).status ?? 'unknown')}</span>
          <span>Gemini/MLLM verifier used: {String(metadata.gemini_mllm_verifier_used ?? false)}</span>
        </div>
      </section>

      <section className="card">
        <div className="panel-header">
          <h3>Reviewed-label comparison</h3>
          <span>Rows with disagreement are listed first.</span>
        </div>
        {comparisonRows.length > 0 ? (
          <div className="demo-table">
            <div className="demo-table-header">
              <span>Requirement</span>
              <span>Prediction</span>
              <span>Reviewed</span>
              <span>Evidence</span>
            </div>
            {comparisonRows.map((row) => (
              <div key={String(row.requirement_id)} className="demo-table-row">
                <strong>{String(row.requirement_id)}</strong>
                <span className={`status-pill ${statusClass(String(row.predicted_label ?? 'unknown'))}`}>{humanizeStatus(String(row.predicted_label ?? 'unknown'))}</span>
                <span className={`status-pill ${statusClass(String(row.reference_label ?? 'unknown'))}`}>{humanizeStatus(String(row.reference_label ?? 'unknown'))}</span>
                <span>
                  <StepChipList stepIndices={(row.predicted_evidence_steps ?? []) as number[]} onJumpToStep={onJumpToStep} />
                </span>
              </div>
            ))}
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
          {demoRun.results.map((result) => (
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
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}

function Metric({label, value}: {label: string; value: string}) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function formatDistribution(distribution: Record<string, number>): string {
  const entries = Object.entries(distribution)
  if (entries.length === 0) {
    return 'none'
  }
  return entries.map(([key, value]) => `${humanizeStatus(key)}: ${value}`).join(', ')
}

function uniqueEvidenceSteps(evidence: {step_index: number}[]): number[] {
  return [...new Set(evidence.map((item) => item.step_index))].sort((a, b) => a - b)
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
  availableSteps: number[]
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
  const [rephrasingClaimIndex, setRephrasingClaimIndex] = useState<number | null>(null)
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
        return {
          ...claim,
          evidenceSteps: claim.evidenceSteps.includes(stepIndex)
            ? claim.evidenceSteps.filter((item) => item !== stepIndex)
            : [...claim.evidenceSteps, stepIndex].sort((a, b) => a - b),
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
                  {availableSteps.map((stepIndex) => {
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
                      {claim.evidenceSteps.length === 0 && ['SUPPORTED', 'CONTRADICTED'].includes(claim.status) && (
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
                        onClick={() => void rephraseClaim(index)}
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
              <button className="secondary-button" onClick={() => onSave('review', candidatePayload)}>
                Save as needs review
              </button>
              <button className="danger-button" onClick={() => onDelete(requirement)}>
                Delete bad requirement
              </button>
              <button onClick={() => onSave('promote', acceptedCandidatePayload)}>Promote to gold</button>
            </>
          ) : (
            <>
              <button className="danger-button" onClick={() => onDelete(requirement)}>
                Delete bad requirement
              </button>
              <button onClick={() => onSave('save_verification_gold', verificationPayload)}>Save verification item</button>
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
            <button className="secondary-button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <img className="lightbox-image" src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`} />
      </div>
    </div>
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
    .replace(/^the system shall\s+/i, '')
    .replace(/^the ui shall\s+/i, '')
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
  return {
    claimId: claim.claim_id ?? '',
    claim: claim.claim_text ?? claim.claim,
    status: claim.status,
    claimType: claim.claim_type ?? 'OBSERVABLE',
    importance: claim.importance ?? 'CORE',
    evidenceSteps: [...(claim.evidence_steps ?? [])],
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
