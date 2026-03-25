import { useEffect, useMemo, useState } from 'react'
import { api, resolveAssetUrl, type FlowStep, type FlowSummary, type Requirement, type VerificationRun } from './api'

type LoadState = 'idle' | 'loading' | 'error'

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([])
  const [flowsState, setFlowsState] = useState<LoadState>('idle')
  const [selectedFlowId, setSelectedFlowId] = useState<string>('')
  const [selectedFlow, setSelectedFlow] = useState<FlowSummary | null>(null)
  const [steps, setSteps] = useState<FlowStep[]>([])
  const [candidates, setCandidates] = useState<Requirement[]>([])
  const [gold, setGold] = useState<Requirement[]>([])
  const [run, setRun] = useState<VerificationRun | null>(null)
  const [detailsState, setDetailsState] = useState<LoadState>('idle')
  const [message, setMessage] = useState<string>('')
  const [annotatedBy, setAnnotatedBy] = useState<string>('benno')
  const [annotationNotes, setAnnotationNotes] = useState<string>('')
  const [maxImages, setMaxImages] = useState<number>(4)

  useEffect(() => {
    void loadFlows()
  }, [])

  useEffect(() => {
    if (!selectedFlowId) {
      return
    }
    void loadFlowDetails(selectedFlowId)
  }, [selectedFlowId])

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
    try {
      const [flow, flowSteps, flowCandidates, flowGold] = await Promise.all([
        api.getFlow(flowId),
        api.getSteps(flowId),
        api.listCandidates(flowId),
        api.listGold(flowId),
      ])
      setSelectedFlow(flow)
      setSteps(flowSteps)
      setCandidates(flowCandidates)
      setGold(flowGold)

      try {
        const latestRun = await api.getLatestVerification(flowId)
        setRun(latestRun)
      } catch {
        setRun(null)
      }

      setDetailsState('idle')
    } catch (error) {
      setDetailsState('error')
      setMessage(error instanceof Error ? error.message : 'Failed to load flow details')
    }
  }

  async function handleCandidateAction(action: 'accept' | 'reject' | 'needs_review', requirementId: string) {
    if (!selectedFlowId) {
      return
    }
    setMessage('')
    try {
      if (action === 'accept') {
        await api.acceptCandidate(selectedFlowId, requirementId, {
          annotation_notes: annotationNotes || undefined,
          annotated_by: annotatedBy || undefined,
        })
      } else if (action === 'reject') {
        await api.rejectCandidate(selectedFlowId, requirementId, {
          reason: annotationNotes || undefined,
          annotated_by: annotatedBy || undefined,
        })
      } else {
        await api.markNeedsReview(selectedFlowId, requirementId)
      }
      await loadFlowDetails(selectedFlowId)
      setMessage(`${requirementId} updated.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to update candidate')
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

  const pendingCandidates = useMemo(
    () => candidates.filter((candidate) => candidate.review_status !== 'accepted' && candidate.review_status !== 'rejected'),
    [candidates],
  )

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
          <div>
            <h2>{selectedFlow?.flow_id ?? 'Select a flow'}</h2>
            <p>{selectedFlow?.confirmed_task ?? 'No task loaded yet.'}</p>
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

        {message && <section className="message card">{message}</section>}
        {detailsState === 'loading' && <section className="card">Loading flow details...</section>}

        <section className="content-grid">
          <section className="card panel-wide">
            <div className="panel-header">
              <h3>Screenshots</h3>
              <span>{steps.length} images</span>
            </div>
            <div className="step-grid">
              {steps.map((step) => (
                <article key={step.step_index} className="step-card">
                  <div className="step-label">Step {step.step_index}</div>
                  <img src={resolveAssetUrl(step.image_url)} alt={`Step ${step.step_index}`} loading="lazy" />
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="panel-header">
              <h3>Candidate requirements</h3>
              <span>{candidates.length}</span>
            </div>
            <div className="requirement-list">
              {candidates.map((requirement) => (
                <RequirementCard
                  key={requirement.requirement_id}
                  requirement={requirement}
                  onAccept={() => void handleCandidateAction('accept', requirement.requirement_id)}
                  onReject={() => void handleCandidateAction('reject', requirement.requirement_id)}
                  onNeedsReview={() => void handleCandidateAction('needs_review', requirement.requirement_id)}
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
                <article key={requirement.requirement_id} className="requirement-card gold-card">
                  <div className="requirement-header">
                    <strong>{requirement.requirement_id}</strong>
                    <span className="status-pill accepted">accepted</span>
                  </div>
                  <p>{requirement.text}</p>
                  <RequirementMeta requirement={requirement} />
                </article>
              ))}
            </div>
          </section>

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
                      <span className={`status-pill ${verdict.label}`}>{verdict.label}</span>
                    </div>
                    {verdict.explanation && <p>{verdict.explanation}</p>}
                    {verdict.evidence.length > 0 && (
                      <ul className="evidence-list">
                        {verdict.evidence.map((evidence, index) => (
                          <li key={`${verdict.requirement_id}-${index}`}>
                            Step {evidence.step_index}: {evidence.reason ?? evidence.evidence_type}
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
        </section>

        <footer className="footer-note card">
          <strong>{pendingCandidates.length}</strong> candidate requirements still need manual review.
        </footer>
      </main>
    </div>
  )
}

function RequirementCard({
  requirement,
  onAccept,
  onReject,
  onNeedsReview,
}: {
  requirement: Requirement
  onAccept: () => void
  onReject: () => void
  onNeedsReview: () => void
}) {
  return (
    <article className="requirement-card">
      <div className="requirement-header">
        <strong>{requirement.requirement_id}</strong>
        <span className={`status-pill ${requirement.review_status ?? 'candidate'}`}>{requirement.review_status ?? 'candidate'}</span>
      </div>
      <p>{requirement.text}</p>
      <RequirementMeta requirement={requirement} />
      <div className="button-row left">
        <button onClick={onAccept}>Accept</button>
        <button className="secondary-button" onClick={onNeedsReview}>Needs review</button>
        <button className="danger-button" onClick={onReject}>Reject</button>
      </div>
    </article>
  )
}

function RequirementMeta({ requirement }: { requirement: Requirement }) {
  return (
    <div className="meta-block">
      <span>Scope: {requirement.scope}</span>
      <span>Steps: {requirement.step_indices.join(', ') || 'none'}</span>
      <span>Tags: {requirement.tags.join(', ') || 'none'}</span>
    </div>
  )
}

export default App
