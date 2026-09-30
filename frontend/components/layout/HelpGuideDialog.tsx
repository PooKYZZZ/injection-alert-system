'use client'

import * as Dialog from '@radix-ui/react-dialog'

interface HelpGuideDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  returnFocusRef: React.RefObject<HTMLButtonElement | null>
}

export function HelpGuideDialog({ open, onOpenChange, returnFocusRef }: HelpGuideDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[60] bg-black/45" />
        <Dialog.Content
          onCloseAutoFocus={(event) => {
            event.preventDefault()
            returnFocusRef.current?.focus()
          }}
          className="fixed inset-y-0 right-0 z-[70] flex w-[min(94vw,440px)] flex-col overflow-y-auto border-l border-border-light bg-surface-panel shadow-2xl focus:outline-none"
        >
          <header className="flex items-start justify-between gap-4 border-b border-border-light px-5 py-5 sm:px-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent-action">CyberTrace guide</p>
              <Dialog.Title className="mt-1 text-xl font-semibold text-text-primary">Help &amp; Guide</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm leading-5 text-text-secondary">
                A quick guide to the dashboard, alerts, and the evidence shown here.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close Help & Guide"
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border-light text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
              >
                <span aria-hidden="true" className="text-lg leading-none">×</span>
              </button>
            </Dialog.Close>
          </header>

          <div className="space-y-6 px-5 py-5 sm:px-6">
            <section aria-labelledby="help-start-heading">
              <h2 id="help-start-heading" className="text-sm font-semibold text-text-primary">Getting started</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Start on Dashboard for a short overview of recent activity. Open Alerts to search, filter, investigate, and triage individual records.
              </p>
            </section>

            <section aria-labelledby="help-dashboard-heading">
              <h2 id="help-dashboard-heading" className="text-sm font-semibold text-text-primary">Dashboard</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Summary cards and the activity chart use the selected time window. Traffic records count stored records; recorded action counts describe labels saved with those records. Select an item in Recent alerts or choose View all alerts to investigate.
              </p>
            </section>

            <section aria-labelledby="help-review-heading">
              <h2 id="help-review-heading" className="text-sm font-semibold text-text-primary">Review an alert</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Open a row to read its request details, model result, related WAF evidence, and available triage controls. If your role allows it, start a review and record a triage outcome.
              </p>
            </section>

            <section aria-labelledby="help-confidence-heading">
              <h2 id="help-confidence-heading" className="text-sm font-semibold text-text-primary">Confidence</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Confidence indicates how strongly the model supports its predicted classification. It does not represent attack severity.
              </p>
            </section>

            <section aria-labelledby="help-waf-heading">
              <h2 id="help-waf-heading" className="text-sm font-semibold text-text-primary">WAF evidence</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Correlated ModSecurity/CRS records can show matched rules and an anomaly score. A missing CRS match means no matching WAF evidence was returned; it does not by itself invalidate a model result.
              </p>
            </section>

            <section aria-labelledby="help-actions-heading">
              <h2 id="help-actions-heading" className="text-sm font-semibold text-text-primary">Recorded action and observed outcome</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                A recorded action is a label stored on the record. An observed HTTP status is the response reported by its producer. The status alone does not identify which system layer enforced a decision.
              </p>
            </section>

            <section aria-labelledby="help-source-heading">
              <h2 id="help-source-heading" className="text-sm font-semibold text-text-primary">Source verification</h2>
              <p className="mt-1 text-sm leading-5 text-text-secondary">
                Source origin names the address source accepted by the backend, such as a verified Cloudflare connecting IP or the direct remote address. Verification describes whether the configured checks accepted that evidence; it does not identify a person behind the address.
              </p>
            </section>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
