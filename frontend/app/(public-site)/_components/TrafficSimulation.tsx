'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useRef, useState } from 'react'

import styles from '@/app/page.module.css'
import {
  TRAFFIC_SIMULATION_SCENARIOS,
  TRAFFIC_SIMULATION_STAGES,
  type TrafficSimulationScenario,
  type TrafficSimulationScenarioId,
} from './trafficSimulationScenarios'

type TriageState = 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive'

const TRIAGE_OPTIONS: { value: TriageState; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'in_review', label: 'In review' },
  { value: 'escalated', label: 'Escalated' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'false_positive', label: 'False positive' },
]

const FINAL_STAGE = TRAFFIC_SIMULATION_STAGES.length - 1
const RECORD_STAGE = 3

function stageExplanation(
  stage: number,
  scenario: TrafficSimulationScenario
): string {
  switch (stage) {
    case 0:
      return 'Review the prepared method, route, and sample input. This is display-only text; the page does not send it anywhere.'
    case 1:
      return scenario.wafFindingIncluded
        ? 'This fictional example includes a linked firewall finding. In the real system, WAF evidence appears only when the available identifiers support that connection.'
        : 'This example has no linked firewall finding. A missing WAF match does not, by itself, prove a request is safe.'
    case 2:
      return `The example model result is ${scenario.prediction} with ${scenario.confidenceTier.toLowerCase()} confidence. Confidence describes support for the classification, not attack severity.`
    case 3:
      return 'A sample Traffic History row brings together the request context and its separate signals. This visitor demo keeps that row in the page only.'
    case 4:
      return 'Traffic Details shows what was recorded while keeping the model result, firewall evidence, saved action, response status, and enforcement source distinct.'
    default:
      return scenario.isSecurityDetection
        ? 'An analyst can record a review state for a security detection. The control below changes only this local sample; it does not update the CyberTrace dashboard.'
        : 'Normal traffic is available for context in Traffic History, but it does not receive the security-detection triage workflow.'
  }
}

export function TrafficSimulation() {
  const [scenarioId, setScenarioId] = useState<TrafficSimulationScenarioId>('sql-injection')
  const [selectedStage, setSelectedStage] = useState(0)
  const [progressStage, setProgressStage] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [triageState, setTriageState] = useState<TriageState>('new')
  const detailsTriggerRef = useRef<HTMLButtonElement>(null)
  const stageButtonRefs = useRef<Array<HTMLButtonElement | null>>([])

  const scenario = TRAFFIC_SIMULATION_SCENARIOS[scenarioId]
  const reachedRecord = progressStage >= RECORD_STAGE
  const complete = progressStage === FINAL_STAGE

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updatePreference = () => setPrefersReducedMotion(preference.matches)
    updatePreference()
    preference.addEventListener('change', updatePreference)
    return () => preference.removeEventListener('change', updatePreference)
  }, [])

  useEffect(() => {
    if (!isPlaying) return

    const timeout = window.setTimeout(() => {
      const nextStage = Math.min(progressStage + 1, FINAL_STAGE)
      setProgressStage(nextStage)
      setSelectedStage(nextStage)
      if (nextStage === FINAL_STAGE) setIsPlaying(false)
    }, 1050)

    return () => window.clearTimeout(timeout)
  }, [isPlaying, progressStage])

  function chooseScenario(nextScenarioId: TrafficSimulationScenarioId) {
    setScenarioId(nextScenarioId)
    setSelectedStage(0)
    setProgressStage(-1)
    setIsPlaying(false)
    setDetailsOpen(false)
    setTriageState('new')
  }

  function advanceOneStage() {
    const nextStage = progressStage < 0 ? 0 : Math.min(progressStage + 1, FINAL_STAGE)
    setProgressStage(nextStage)
    setSelectedStage(nextStage)
  }

  function handleRunControl() {
    if (isPlaying) {
      setIsPlaying(false)
      return
    }

    if (prefersReducedMotion) {
      if (complete) {
        setProgressStage(-1)
        setSelectedStage(0)
        setDetailsOpen(false)
        setTriageState('new')
      } else {
        advanceOneStage()
      }
      return
    }

    if (complete || progressStage < 0) {
      setProgressStage(0)
      setSelectedStage(0)
      setDetailsOpen(false)
      setTriageState('new')
    }
    setIsPlaying(true)
  }

  function resetSimulation() {
    setProgressStage(-1)
    setSelectedStage(0)
    setIsPlaying(false)
    setDetailsOpen(false)
    setTriageState('new')
  }

  function handleStageKeyDown(
    event: React.KeyboardEvent<HTMLButtonElement>,
    stageIndex: number
  ) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const direction = event.key === 'ArrowRight' ? 1 : -1
    const nextStage = Math.max(0, Math.min(FINAL_STAGE, stageIndex + direction))
    setSelectedStage(nextStage)
    stageButtonRefs.current[nextStage]?.focus()
  }

  const runLabel = isPlaying
    ? 'Pause walkthrough'
    : prefersReducedMotion
      ? complete
        ? 'Replay walkthrough'
        : progressStage < 0
          ? 'Start walkthrough'
          : 'Next stage'
      : complete
        ? 'Replay walkthrough'
        : progressStage < 0
          ? 'Start walkthrough'
          : 'Resume walkthrough'

  const progressAnnouncement = progressStage < 0
    ? 'Ready. Choose a scenario and start the walkthrough.'
    : complete
      ? 'Walkthrough complete. The sample remains on this page only.'
      : isPlaying || prefersReducedMotion
        ? `Step ${progressStage + 1} of ${TRAFFIC_SIMULATION_STAGES.length}: ${TRAFFIC_SIMULATION_STAGES[progressStage].title}.`
        : `Paused at step ${progressStage + 1} of ${TRAFFIC_SIMULATION_STAGES.length}: ${TRAFFIC_SIMULATION_STAGES[progressStage].title}.`

  return (
    <section className={styles.simulation} aria-labelledby="simulation-title" data-testid="traffic-simulation">
      <header className={styles.simulationHeader}>
        <div>
          <p className={styles.simulationEyebrow}>INTERACTIVE WALKTHROUGH · SAMPLE DATA</p>
          <h2 id="simulation-title">Follow a request from signal to review.</h2>
          <p className={styles.simulationIntroCopy}>
            Choose an example and see how its separate signals become a record an analyst can inspect.
          </p>
        </div>
        <p className={styles.simulationSafety}>
          <span aria-hidden="true">●</span> Nothing is sent or saved.
        </p>
      </header>

      <div className={styles.simulationWorkbench}>
        <aside className={styles.simulationRequestPanel} aria-labelledby="simulation-request-title">
          <p className={styles.simulationPanelEyebrow}>01 / PICK A SAMPLE</p>
          <h3 id="simulation-request-title">Choose a request</h3>
          <div className={styles.simulationScenarioList} aria-label="Sample request scenarios">
            {Object.values(TRAFFIC_SIMULATION_SCENARIOS).map((sample) => (
              <button
                aria-pressed={sample.id === scenarioId}
                className={[
                  styles.simulationScenario,
                  sample.id === scenarioId ? styles.simulationScenarioSelected : '',
                ].filter(Boolean).join(' ')}
                key={sample.id}
                onClick={() => chooseScenario(sample.id)}
                type="button"
              >
                <span className={styles.simulationRadio} aria-hidden="true" />
                <span className={styles.simulationScenarioText}>
                  <strong>{sample.title}</strong>
                  <span>{sample.summary}</span>
                </span>
              </button>
            ))}
          </div>

          <div className={styles.simulationRequestPreview} aria-label="Prepared request preview">
            <div className={styles.simulationPreviewTop}>
              <span>REQUEST PREVIEW</span>
              <span>sample-store.example.test</span>
            </div>
            <code>{scenario.method} {scenario.path}</code>
            {scenario.body && <pre>{scenario.body}</pre>}
            <p>Prepared for this walkthrough · never transmitted</p>
          </div>

          <div className={styles.simulationControls}>
            <button className={styles.simulationPrimaryButton} onClick={handleRunControl} type="button">
              <span className={styles.simulationControlIcon} aria-hidden="true">
                {isPlaying ? 'Ⅱ' : complete ? '↻' : '▶'}
              </span>
              <span>{runLabel}</span>
            </button>
            <button className={styles.simulationResetButton} onClick={resetSimulation} type="button">
              Reset
            </button>
          </div>
          {prefersReducedMotion && (
            <p className={styles.simulationMotionNote}>
              Reduced motion is on. Move through one stage at a time.
            </p>
          )}
        </aside>

        <div className={styles.simulationFlowPanel}>
          <div className={styles.simulationFlowHeading}>
            <div>
              <p className={styles.simulationPanelEyebrow}>02 / FOLLOW THE REVIEW PATH</p>
              <h3>Different signals. One reviewable record.</h3>
            </div>
            <span className={styles.simulationDemoTag}>DEMO</span>
          </div>

          <ol className={styles.simulationTimeline} aria-label="Simulation stages">
            {TRAFFIC_SIMULATION_STAGES.map((stage, index) => {
              const reached = progressStage >= index
              const current = progressStage === index
              return (
                <li className={styles.simulationTimelineItem} key={stage.label}>
                  <button
                    aria-current={current ? 'step' : undefined}
                    aria-pressed={selectedStage === index}
                    className={[
                      styles.simulationStageButton,
                      selectedStage === index ? styles.simulationStageSelected : '',
                      reached ? styles.simulationStageReached : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => setSelectedStage(index)}
                    onKeyDown={(event) => handleStageKeyDown(event, index)}
                    ref={(element) => { stageButtonRefs.current[index] = element }}
                    type="button"
                  >
                    <span className={styles.simulationStageNumber}>{String(index + 1).padStart(2, '0')}</span>
                    <span>{stage.label}</span>
                  </button>
                </li>
              )
            })}
          </ol>

          <div className={styles.simulationStageDetail}>
            <div className={styles.simulationStageDetailHeader}>
              <div>
                <p className={styles.simulationPanelEyebrow}>STEP {String(selectedStage + 1).padStart(2, '0')}</p>
                <h4>{TRAFFIC_SIMULATION_STAGES[selectedStage].title}</h4>
              </div>
              <span className={styles.simulationStageState}>
                {progressStage >= selectedStage ? 'Reached in sample' : 'Explore this step'}
              </span>
            </div>
            <p>{stageExplanation(selectedStage, scenario)}</p>
            <p className={styles.simulationLiveStatus} role="status" aria-live="polite">
              {progressAnnouncement}
            </p>
          </div>

          {reachedRecord ? (
            <div className={styles.simulationRecord}>
              <div className={styles.simulationRecordHeading}>
                <div>
                  <p className={styles.simulationPanelEyebrow}>TRAFFIC HISTORY · SAMPLE RECORD</p>
                  <strong>{scenario.isSecurityDetection ? 'Security detection' : 'Normal traffic'}</strong>
                </div>
                <span className={styles.simulationSyntheticTag}>SYNTHETIC</span>
              </div>
              <div className={styles.simulationRecordSummary}>
                <code>{scenario.method} {scenario.path}</code>
                <span className={styles.simulationPrediction}>{scenario.prediction}</span>
                <span className={styles.simulationConfidence}>{scenario.confidenceTier}</span>
                <span className={styles.simulationAction}>{scenario.recordedAction}</span>
              </div>
              <div className={styles.simulationRecordFooter}>
                <p>This record exists only in this page demo.</p>
                <button
                  ref={detailsTriggerRef}
                  className={styles.simulationDetailsButton}
                  onClick={() => setDetailsOpen(true)}
                  type="button"
                >
                  Open Traffic Details <span aria-hidden="true">↗</span>
                </button>
              </div>
            </div>
          ) : (
            <div className={styles.simulationRecordPlaceholder}>
              <span className={styles.simulationPlaceholderIcon} aria-hidden="true">↳</span>
              <p>The sample record will appear here after the signals are reviewed.</p>
            </div>
          )}
        </div>
      </div>

      <Dialog.Root open={detailsOpen} onOpenChange={setDetailsOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className={styles.simulationDialogOverlay} />
          <Dialog.Content
            className={styles.simulationDialog}
            onCloseAutoFocus={(event) => {
              event.preventDefault()
              detailsTriggerRef.current?.focus()
            }}
          >
            <div className={styles.simulationDialogHeader}>
              <div>
                <p className={styles.simulationPanelEyebrow}>SYNTHETIC SAMPLE · TRAFFIC DETAILS</p>
                <Dialog.Title className={styles.simulationDialogTitle}>
                  {scenario.method} {scenario.path}
                </Dialog.Title>
                <Dialog.Description className={styles.simulationDialogDescription}>
                  Example record for learning the review flow. It was not created by a live request.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button className={styles.simulationDialogClose} aria-label="Close Traffic Details" type="button">×</button>
              </Dialog.Close>
            </div>

            <div className={styles.simulationDetailGrid}>
              <section className={styles.simulationDetailBlock}>
                <h3>Request context</h3>
                <dl>
                  <div><dt>Method</dt><dd>{scenario.method}</dd></div>
                  <div><dt>Route</dt><dd><code>{scenario.path}</code></dd></div>
                  <div><dt>Source</dt><dd>192.0.2.44 · example address</dd></div>
                  {scenario.body && <div className={styles.simulationBodyDetail}><dt>Captured input</dt><dd><pre>{scenario.body}</pre></dd></div>}
                </dl>
              </section>
              <section className={styles.simulationDetailBlock}>
                <h3>Model suggestion</h3>
                <dl>
                  <div><dt>Prediction</dt><dd>{scenario.prediction}</dd></div>
                  <div><dt>Confidence tier</dt><dd>{scenario.confidenceTier}</dd></div>
                </dl>
                <p>Confidence supports the model’s label; it is not a measure of attack severity.</p>
              </section>
              <section className={styles.simulationDetailBlock}>
                <h3>Firewall evidence</h3>
                <p>
                  {scenario.wafFindingIncluded
                    ? 'This sample includes a fictional linked CRS finding.'
                    : 'No linked WAF finding is included in this sample.'}
                </p>
                <p>Real evidence is shown only when recorded details can be linked to the request.</p>
              </section>
              <section className={styles.simulationDetailBlock}>
                <h3>Action and outcome</h3>
                <dl>
                  <div><dt>Recorded action</dt><dd>{scenario.recordedAction}</dd></div>
                  <div><dt>Observed HTTP status</dt><dd>Not measured</dd></div>
                  <div><dt>Enforcement source</dt><dd>Not established by this demo</dd></div>
                </dl>
                <p>The stored action label does not prove the request was blocked.</p>
              </section>
            </div>

            <section className={styles.simulationTriage} aria-labelledby="simulation-triage-title">
              <div>
                <h3 id="simulation-triage-title">Analyst review</h3>
                <p>
                  {scenario.isSecurityDetection
                    ? progressStage >= FINAL_STAGE
                      ? 'Try a review state. This change stays in your browser and is not sent to CyberTrace.'
                      : 'Continue the walkthrough to Analyst review to try a sample state.'
                    : 'Normal traffic remains read-only and does not use the security triage workflow.'}
                </p>
              </div>
              {scenario.isSecurityDetection ? (
                <label className={styles.simulationTriageControl}>
                  <span>Sample review state</span>
                  <select
                    aria-label="Sample review state"
                    disabled={progressStage < FINAL_STAGE}
                    onChange={(event) => setTriageState(event.target.value as TriageState)}
                    value={triageState}
                  >
                    {TRIAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              ) : (
                <span className={styles.simulationReadOnly}>Read-only sample</span>
              )}
            </section>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  )
}
