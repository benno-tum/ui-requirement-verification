import {useEffect, useMemo, useState, type ReactNode} from 'react'
import {
    api,
    resolveAssetUrl,
    type FlowStep,
    type FlowSummary,
    type ManualVerdictLabel,
    type Requirement,
    type HarvestedRequirement,
    type RequirementPayload,
    type RequirementVerdict,
    type VerificationRun,
} from './api'

type LoadState = 'idle' | 'loading' | 'error'
type ViewMode = 'single' | 'multi' | 'overview' | 'verification' | 'harvested'
type EditorMode = 'candidate' | 'gold'

type EditorState = {
    mode: EditorMode
    requirement: Requirement
}

type RequirementFormState = {
    text: string
    stepIndices: number[]
    tags: string
    annotationNotes: string
    annotatedBy: string
    manualVerificationLabel: ManualVerdictLabel
    manualVerificationNotes: string
}

const VIEW_TABS: Array<{ id: ViewMode; label: string }> = [
    {id: 'single', label: 'Single-screen review'},
    {id: 'multi', label: 'Multi-screen review'},
    {id: 'overview', label: 'Overview'},
    {id: 'verification', label: 'Verification results'},
    {id: 'harvested', label: 'Harvested'},
]

function App() {
    const [flows, setFlows] = useState<FlowSummary[]>([])
    const [flowsState, setFlowsState] = useState<LoadState>('idle')
    const [selectedFlowId, setSelectedFlowId] = useState<string>('')
    const [selectedFlow, setSelectedFlow] = useState<FlowSummary | null>(null)
    const [steps, setSteps] = useState<FlowStep[]>([])
    const [harvested, setHarvested] = useState<HarvestedRequirement[]>([])
    const [candidates, setCandidates] = useState<Requirement[]>([])
    const [gold, setGold] = useState<Requirement[]>([])
    const [run, setRun] = useState<VerificationRun | null>(null)
    const [detailsState, setDetailsState] = useState<LoadState>('idle')
    const [message, setMessage] = useState<string>('')
    const [annotatedBy, setAnnotatedBy] = useState<string>('benno')
    const [annotationNotes, setAnnotationNotes] = useState<string>('')
    const [maxImages, setMaxImages] = useState<number>(4)
    const [viewMode, setViewMode] = useState<ViewMode>('single')
    const [highlightedStep, setHighlightedStep] = useState<number | null>(null)
    const [zoomStep, setZoomStep] = useState<FlowStep | null>(null)
    const [editor, setEditor] = useState<EditorState | null>(null)

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
            if (!selectedFlowId && data.length > 0) {
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
        setGold([])
        setRun(null)

        try {
            const flow = await api.getFlow(flowId)
            setSelectedFlow(flow)

            const [stepsResult, harvestedResult, candidatesResult, goldResult, runResult] = await Promise.allSettled([
                api.getSteps(flowId),
                api.listHarvested(flowId),
                api.listCandidates(flowId),
                api.listGold(flowId),
                api.getLatestVerification(flowId),
            ])

            if (stepsResult.status === 'fulfilled') {
                setSteps(stepsResult.value)
            }

            if (harvestedResult.status === 'fulfilled') {
                setHarvested(harvestedResult.value)
            } else {
                setHarvested([])
            }

            if (candidatesResult.status === 'fulfilled') {
                setCandidates(candidatesResult.value)
            } else {
                setCandidates([])
            }

            if (goldResult.status === 'fulfilled') {
                setGold(goldResult.value)
            } else {
                setGold([])
            }

            if (runResult.status === 'fulfilled') {
                setRun(runResult.value)
            } else {
                setRun(null)
            }

            setDetailsState('idle')
        } catch (error) {
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

    async function handleSaveEditor(action: 'review' | 'promote' | 'save_gold', payload: RequirementPayload) {
        if (!selectedFlowId || !editor) {
            return
        }

        setMessage('')
        const requirementId = editor.requirement.requirement_id

        try {
            if (editor.mode === 'candidate' && action === 'review') {
                await api.reviewCandidate(selectedFlowId, requirementId, payload)
                setMessage(`${requirementId} saved for review.`)
            } else if (editor.mode === 'candidate' && action === 'promote') {
                await api.acceptCandidate(selectedFlowId, requirementId, payload)
                setMessage(`${requirementId} promoted to gold.`)
            } else if (editor.mode === 'gold' && action === 'save_gold') {
                await api.updateGoldRequirement(selectedFlowId, requirementId, payload)
                setMessage(`${requirementId} gold requirement updated.`)
            }

            setEditor(null)
            await loadFlowDetails(selectedFlowId)
        } catch (error) {
            setMessage(error instanceof Error ? error.message : 'Failed to save requirement changes')
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

    async function handleVerify(dryRun: boolean) {
        if (!selectedFlow) {
            return
        }
        setMessage('')
        try {
            const result = await api.verify({
                flow_dir: selectedFlow.flow_dir,
                max_images: maxImages,
                dry_run: dryRun,
            })
            if ('verdicts' in result) {
                setRun(result)
                setMessage(`Verification completed for ${selectedFlow.flow_id}.`)
            } else {
                setMessage(`Dry run completed for ${selectedFlow.flow_id}.`)
            }
            await loadFlowDetails(selectedFlow.flow_id)
        } catch (error) {
            setMessage(error instanceof Error ? error.message : 'Verification failed')
        }
    }

    const activeCandidates = useMemo(
        () => candidates.filter((candidate) => candidate.review_status !== 'accepted' && candidate.review_status !== 'rejected'),
        [candidates],
    )

    const singleScreenCandidates = useMemo(
        () => activeCandidates.filter((candidate) => candidate.step_indices.length <= 1),
        [activeCandidates],
    )

    const multiScreenCandidates = useMemo(
        () => activeCandidates.filter((candidate) => candidate.step_indices.length > 1),
        [activeCandidates],
    )

    const singleScreenGold = useMemo(() => gold.filter((requirement) => requirement.step_indices.length <= 1), [gold])
    const multiScreenGold = useMemo(() => gold.filter((requirement) => requirement.step_indices.length > 1), [gold])

    const candidateGroupsByStep = useMemo(() => groupRequirementsBySingleStep(singleScreenCandidates), [singleScreenCandidates])
    const goldGroupsByStep = useMemo(() => groupRequirementsBySingleStep(singleScreenGold), [singleScreenGold])
    const verdictMap = useMemo(() => new Map((run?.verdicts ?? []).map((verdict) => [verdict.requirement_id, verdict])), [run])

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <div className="sidebar-header">
                    <h1>UI Verifier</h1>
                    <p>Annotation and verification workbench</p>
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
                {flow.gold_count}/{flow.candidate_count} gold
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
                            <span className="mini-label">Dataset decision</span>
                            <strong>candidate → gold</strong>
                            <span className="mini-label">Verification verdict</span>
                            <strong>fulfilled / partial / not fulfilled / abstain</strong>
                        </div>
                    </div>

                    <div className="toolbar-grid">
                        <label>
                            Annotated by
                            <input value={annotatedBy} onChange={(event) => setAnnotatedBy(event.target.value)}
                                   placeholder="annotator"/>
                        </label>
                        <label>
                            Notes
                            <input value={annotationNotes} onChange={(event) => setAnnotationNotes(event.target.value)}
                                   placeholder="optional note"/>
                        </label>
                        <label>
                            Max images
                            <input
                                type="number"
                                min={1}
                                value={maxImages}
                                onChange={(event) => setMaxImages(Number(event.target.value) || 1)}
                            />
                        </label>
                        <div className="button-row">
                            <button onClick={() => void handleVerify(true)}>Verify dry run</button>
                            <button onClick={() => void handleVerify(false)}>Run verification</button>
                        </div>
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
                        onEditGold={(requirement) => setEditor({mode: 'gold', requirement})}
                        verdictMap={verdictMap}
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
                        onEditGold={(requirement) => setEditor({mode: 'gold', requirement})}
                        verdictMap={verdictMap}
                    />
                )}

                {selectedFlow && viewMode === 'overview' && (
                    <OverviewPanel
                        steps={steps}
                        activeCandidates={activeCandidates}
                        gold={gold}
                        onJumpToStep={jumpToStep}
                        onOpenZoom={setZoomStep}
                        onPromote={(requirement) => void handleCandidateAction('accept', requirement)}
                        onEditCandidate={(requirement) => setEditor({mode: 'candidate', requirement})}
                        onReject={(requirement) => void handleCandidateAction('reject', requirement)}
                        onEditGold={(requirement) => setEditor({mode: 'gold', requirement})}
                        verdictMap={verdictMap}
                    />
                )}

                {selectedFlow && viewMode === 'verification' &&
                    <VerificationPanel run={run} onJumpToStep={jumpToStep}/>}

                {selectedFlow && viewMode === 'harvested' && (
                    <HarvestedPanel
                        harvested={harvested}
                        onJumpToStep={jumpToStep}
                        onMaterialize={() => void handleMaterializeCandidatesFromHarvested()}
                    />
                )}

                <footer className="footer-note card">
                    <strong>{activeCandidates.length}</strong> candidate requirements still need manual review.
                </footer>
            </main>

            {zoomStep && <ImageLightbox step={zoomStep} onClose={() => setZoomStep(null)}/>}
            {editor && (
                <RequirementEditorModal
                    mode={editor.mode}
                    requirement={editor.requirement}
                    availableSteps={steps.map((step) => step.step_index)}
                    defaultAnnotatedBy={annotatedBy}
                    onClose={() => setEditor(null)}
                    onSave={(action, payload) => void handleSaveEditor(action, payload)}
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
                                onOpenZoom,
                                onJumpToStep,
                                onPromote,
                                onEditCandidate,
                                onReject,
                                onEditGold,
                                verdictMap,
                            }: {
    steps: FlowStep[]
    highlightedStep: number | null
    candidatesByStep: Map<number, Requirement[]>
    goldByStep: Map<number, Requirement[]>
    onOpenZoom: (step: FlowStep) => void
    onJumpToStep: (stepIndex: number) => void
    onPromote: (requirement: Requirement) => void
    onEditCandidate: (requirement: Requirement) => void
    onReject: (requirement: Requirement) => void
    onEditGold: (requirement: Requirement) => void
    verdictMap: Map<string, RequirementVerdict>
}) {
    return (
        <section className="stack-layout">
            <section className="card sticky-card">
                <div className="panel-header">
                    <h3>Flow screens</h3>
                    <span>Click a step to jump. Click an image to zoom.</span>
                </div>
                <div className="chip-row">
                    {steps.map((step) => (
                        <button key={step.step_index} className="step-chip"
                                onClick={() => onJumpToStep(step.step_index)}>
                            Step {step.step_index}
                        </button>
                    ))}
                </div>
            </section>

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
                                <span>{stepCandidates.length} pending single-screen candidates · {stepGold.length} gold requirements</span>
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
                                                verdict={verdictMap.get(requirement.requirement_id)}
                                                actions={
                                                    <div className="button-row left wrap">
                                                        <button onClick={() => onPromote(requirement)}>Promote to gold
                                                        </button>
                                                        <button className="secondary-button"
                                                                onClick={() => onEditCandidate(requirement)}>
                                                            Edit / review
                                                        </button>
                                                        <button className="danger-button"
                                                                onClick={() => onReject(requirement)}>
                                                            Reject
                                                        </button>
                                                    </div>
                                                }
                                            />
                                        ))}
                                    </div>
                                ) : (
                                    <p className="empty-text">No pending single-screen candidates linked to this
                                        step.</p>
                                )}
                            </section>

                            <section className="linked-column">
                                <div className="subsection-header">
                                    <h4>Gold requirements</h4>
                                    <span>{stepGold.length}</span>
                                </div>
                                {stepGold.length > 0 ? (
                                    <div className="requirement-list compact-list">
                                        {stepGold.map((requirement) => (
                                            <RequirementCard
                                                key={requirement.requirement_id}
                                                requirement={requirement}
                                                onJumpToStep={onJumpToStep}
                                                verdict={verdictMap.get(requirement.requirement_id)}
                                                actions={
                                                    <div className="button-row left wrap">
                                                        <button className="secondary-button"
                                                                onClick={() => onEditGold(requirement)}>
                                                            Edit gold labels
                                                        </button>
                                                    </div>
                                                }
                                            />
                                        ))}
                                    </div>
                                ) : (
                                    <p className="empty-text">No gold requirements linked to this step yet.</p>
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
                               verdictMap,
                           }: {
    steps: FlowStep[]
    candidates: Requirement[]
    gold: Requirement[]
    onJumpToStep: (stepIndex: number) => void
    onEditCandidate: (requirement: Requirement) => void
    onPromote: (requirement: Requirement) => void
    onReject: (requirement: Requirement) => void
    onEditGold: (requirement: Requirement) => void
    verdictMap: Map<string, RequirementVerdict>
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
                        <button key={step.step_index} className="step-chip"
                                onClick={() => onJumpToStep(step.step_index)}>
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
                                verdict={verdictMap.get(requirement.requirement_id)}
                                actions={
                                    <div className="button-row left wrap">
                                        <button onClick={() => onPromote(requirement)}>Promote to gold</button>
                                        <button className="secondary-button"
                                                onClick={() => onEditCandidate(requirement)}>
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
                    <h3>Gold multi-screen requirements</h3>
                    <span>{gold.length}</span>
                </div>
                <div className="requirement-list compact-list">
                    {gold.length > 0 ? (
                        gold.map((requirement) => (
                            <RequirementCard
                                key={requirement.requirement_id}
                                requirement={requirement}
                                onJumpToStep={onJumpToStep}
                                verdict={verdictMap.get(requirement.requirement_id)}
                                actions={
                                    <div className="button-row left wrap">
                                        <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                                            Edit gold labels
                                        </button>
                                    </div>
                                }
                            />
                        ))
                    ) : (
                        <p className="empty-text">No gold multi-screen requirements yet.</p>
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
                           verdictMap,
                       }: {
    steps: FlowStep[]
    activeCandidates: Requirement[]
    gold: Requirement[]
    onJumpToStep: (stepIndex: number) => void
    onOpenZoom: (step: FlowStep) => void
    onPromote: (requirement: Requirement) => void
    onEditCandidate: (requirement: Requirement) => void
    onReject: (requirement: Requirement) => void
    onEditGold: (requirement: Requirement) => void
    verdictMap: Map<string, RequirementVerdict>
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
                        <article key={step.step_index} className="step-card compact-step-card">
                            <div className="step-label">Step {step.step_index}</div>
                            <img src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`} loading="lazy"
                                 onClick={() => onOpenZoom(step)}/>
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
                            verdict={verdictMap.get(requirement.requirement_id)}
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
                    <h3>Gold requirements</h3>
                    <span>{gold.length}</span>
                </div>
                <div className="requirement-list compact-list">
                    {gold.map((requirement) => (
                        <RequirementCard
                            key={requirement.requirement_id}
                            requirement={requirement}
                            onJumpToStep={onJumpToStep}
                            verdict={verdictMap.get(requirement.requirement_id)}
                            actions={
                                <div className="button-row left wrap">
                                    <button className="secondary-button" onClick={() => onEditGold(requirement)}>
                                        Edit gold labels
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
    onJumpToStep,
    onMaterialize,
}: {
    harvested: HarvestedRequirement[]
    onJumpToStep: (stepIndex: number) => void
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
                    <button onClick={onMaterialize} disabled={harvested.length === 0}>
                        Replace candidates from harvested
                    </button>
                </div>
                <p className="inline-note">
                    These are the broader hypotheses produced from the UI flow before candidate normalization.
                </p>
                {harvested.length > 0 ? (
                    <div className="requirement-list compact-list">
                        {harvested.map((item) => (
                            <article key={item.harvest_id} className="requirement-card">
                                <div className="requirement-header">
                                    <strong>{item.harvest_id}</strong>
                                    <div className="pill-row">
                                        <span className={`status-pill ${item.ui_evaluability?.toLowerCase?.() ?? ''}`}>
                                            {humanizeStatus(item.ui_evaluability)}
                                        </span>
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
                                {item.visible_core_candidate && (
                                    <p className="inline-note">Visible-core rewrite suggestion: {item.visible_core_candidate}</p>
                                )}
                                {item.non_evaluable_reason && item.non_evaluable_reason !== 'NONE' && (
                                    <p className="inline-note">Limitation: {humanizeStatus(item.non_evaluable_reason)}</p>
                                )}
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

function VerificationPanel({run, onJumpToStep}: {
    run: VerificationRun | null;
    onJumpToStep: (stepIndex: number) => void
}) {
    return (
        <section className="card panel-wide">
            <div className="panel-header">
                <h3>Latest verification run</h3>
                <span>{run ? run.created_at : 'none'}</span>
            </div>
            {run ? (
                <div className="requirement-list compact-list">
                    {run.verdicts.map((verdict) => (
                        <article key={verdict.requirement_id} className="requirement-card">
                            <div className="requirement-header">
                                <strong>{verdict.requirement_id}</strong>
                                <span className={`status-pill ${verdict.label}`}>{humanizeStatus(verdict.label)}</span>
                            </div>
                            {verdict.explanation && <p>{verdict.explanation}</p>}
                            {verdict.evidence.length > 0 && (
                                <ul className="evidence-list">
                                    {verdict.evidence.map((evidence, index) => (
                                        <li key={`${verdict.requirement_id}-${index}`}>
                                            <button className="link-button"
                                                    onClick={() => onJumpToStep(evidence.step_index)}>
                                                Step {evidence.step_index}
                                            </button>
                                            {' '}
                                            {evidence.reason ?? evidence.evidence_type}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </article>
                    ))}
                </div>
            ) : (
                <p>No verification run stored for this flow yet.</p>
            )}
        </section>
    )
}

function RequirementCard({
                             requirement,
                             actions,
                             onJumpToStep,
                             verdict,
                         }: {
    requirement: Requirement
    actions?: ReactNode
    onJumpToStep: (stepIndex: number) => void
    verdict?: RequirementVerdict
}) {
    return (
        <article className="requirement-card">
            <div className="requirement-header">
                <strong>{requirement.requirement_id}</strong>
                <div className="pill-row">
                    <span
                        className={`status-pill ${requirement.review_status ?? 'candidate'}`}>{humanizeStatus(requirement.review_status ?? 'candidate')}</span>
                    {requirement.manual_verification_label && (
                        <span
                            className={`status-pill manual ${requirement.manual_verification_label}`}>manual: {humanizeStatus(requirement.manual_verification_label)}</span>
                    )}
                    {verdict &&
                        <span className={`status-pill ${verdict.label}`}>run: {humanizeStatus(verdict.label)}</span>}
                </div>
            </div>
            <p>{requirement.text}</p>
            <RequirementMeta requirement={requirement} onJumpToStep={onJumpToStep}/>
            {requirement.manual_verification_notes &&
                <p className="inline-note">Manual verdict notes: {requirement.manual_verification_notes}</p>}
            {actions}
        </article>
    )
}

function RequirementMeta({requirement, onJumpToStep}: {
    requirement: Requirement;
    onJumpToStep: (stepIndex: number) => void
}) {
    return (
        <div className="meta-block">
            <span>Scope: {requirement.scope}</span>
            <span>
        Steps:{' '}
                <StepChipList stepIndices={requirement.step_indices} onJumpToStep={onJumpToStep}/>
      </span>
            <span>Tags: {requirement.tags.join(', ') || 'none'}</span>
        </div>
    )
}

function StepChipList({stepIndices, onJumpToStep}: {
    stepIndices: number[];
    onJumpToStep: (stepIndex: number) => void
}) {
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
                                }: {
    mode: EditorMode
    requirement: Requirement
    availableSteps: number[]
    defaultAnnotatedBy: string
    onClose: () => void
    onSave: (action: 'review' | 'promote' | 'save_gold', payload: RequirementPayload) => void
}) {
    const [form, setForm] = useState<RequirementFormState>(() => ({
        text: requirement.text,
        stepIndices: [...requirement.step_indices],
        tags: requirement.tags.join(', '),
        annotationNotes: requirement.annotation_notes ?? requirement.rationale ?? '',
        annotatedBy: requirement.annotated_by ?? defaultAnnotatedBy,
        manualVerificationLabel: requirement.manual_verification_label ?? '',
        manualVerificationNotes: requirement.manual_verification_notes ?? '',
    }))

    function toggleStep(stepIndex: number) {
        setForm((current) => ({
            ...current,
            stepIndices: current.stepIndices.includes(stepIndex)
                ? current.stepIndices.filter((item) => item !== stepIndex)
                : [...current.stepIndices, stepIndex].sort((a, b) => a - b),
        }))
    }

    const payload: RequirementPayload = {
        edited_text: form.text.trim(),
        edited_step_indices: form.stepIndices,
        edited_tags: parseTags(form.tags),
        annotation_notes: form.annotationNotes.trim() || undefined,
        annotated_by: form.annotatedBy.trim() || undefined,
        manual_verification_label: form.manualVerificationLabel || undefined,
        manual_verification_notes: form.manualVerificationNotes.trim() || undefined,
    }

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-card" onClick={(event) => event.stopPropagation()}>
                <div className="panel-header align-start">
                    <div>
                        <h3>{mode === 'candidate' ? 'Review candidate requirement' : 'Edit gold requirement'}</h3>
                        <span>{requirement.requirement_id}</span>
                    </div>
                    <button className="secondary-button" onClick={onClose}>
                        Close
                    </button>
                </div>

                <div className="editor-grid">
                    <label>
                        Requirement text
                        <textarea value={form.text} onChange={(event) => setForm({...form, text: event.target.value})}
                                  rows={4}/>
                    </label>

                    <label>
                        Tags (comma separated)
                        <input value={form.tags} onChange={(event) => setForm({...form, tags: event.target.value})}/>
                    </label>

                    <label>
                        Annotated by
                        <input value={form.annotatedBy}
                               onChange={(event) => setForm({...form, annotatedBy: event.target.value})}/>
                    </label>

                    <label>
                        Notes
                        <textarea value={form.annotationNotes}
                                  onChange={(event) => setForm({...form, annotationNotes: event.target.value})}
                                  rows={3}/>
                    </label>

                    <fieldset className="step-picker">
                        <legend>Linked steps</legend>
                        <div className="chip-row">
                            {availableSteps.map((stepIndex) => {
                                const selected = form.stepIndices.includes(stepIndex)
                                return (
                                    <button
                                        type="button"
                                        key={stepIndex}
                                        className={selected ? 'step-chip selected' : 'step-chip'}
                                        onClick={() => toggleStep(stepIndex)}
                                    >
                                        Step {stepIndex}
                                    </button>
                                )
                            })}
                        </div>
                    </fieldset>

                    <label>
                        Manual verification label
                        <select
                            value={form.manualVerificationLabel}
                            onChange={(event) =>
                                setForm({...form, manualVerificationLabel: event.target.value as ManualVerdictLabel})
                            }
                        >
                            <option value="">not set</option>
                            <option value="fulfilled">fulfilled</option>
                            <option value="partially_fulfilled">partially fulfilled</option>
                            <option value="not_fulfilled">not fulfilled</option>
                            <option value="abstain">abstain</option>
                        </select>
                    </label>

                    <label>
                        Manual verification notes
                        <textarea
                            value={form.manualVerificationNotes}
                            onChange={(event) => setForm({...form, manualVerificationNotes: event.target.value})}
                            rows={3}
                        />
                    </label>
                </div>

                <div className="button-row wrap">
                    {mode === 'candidate' ? (
                        <>
                            <button className="secondary-button" onClick={() => onSave('review', payload)}>
                                Save as needs review
                            </button>
                            <button onClick={() => onSave('promote', payload)}>Promote to gold</button>
                        </>
                    ) : (
                        <button onClick={() => onSave('save_gold', payload)}>Save gold requirement</button>
                    )}
                </div>
            </div>
        </div>
    )
}

function ImageLightbox({step, onClose}: { step: FlowStep; onClose: () => void }) {
    return (
        <div className="modal-backdrop lightbox-backdrop" onClick={onClose}>
            <div className="lightbox-card" onClick={(event) => event.stopPropagation()}>
                <div className="panel-header align-start">
                    <div>
                        <h3>Step {step.step_index}</h3>
                        <span>{step.image_name}</span>
                    </div>
                    <button className="secondary-button" onClick={onClose}>
                        Close
                    </button>
                </div>
                <img className="lightbox-image" src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`}/>
            </div>
        </div>
    )
}

function groupRequirementsBySingleStep(requirements: Requirement[]): Map<number, Requirement[]> {
    const groups = new Map<number, Requirement[]>()
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

function parseTags(value: string): string[] {
    return value
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
}

function humanizeStatus(value: string): string {
    return value.replace(/_/g, ' ')
}

export default App
