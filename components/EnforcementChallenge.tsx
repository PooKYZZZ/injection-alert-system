"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import {
  challengeUiAction,
  removeTurnstileWidget,
  type BrowserChallengeStatus,
} from "../lib/enforcement-challenge-ui";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          action: string;
          callback: (token: string) => void;
          "error-callback"?: () => void;
          "expired-callback"?: () => void;
        },
      ) => string;
      reset: (widgetId?: string) => void;
      remove: (widgetId?: string) => void;
    };
  }
}

export function EnforcementChallenge({ siteKey }: { siteKey: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | undefined>(undefined);
  const [scriptReady, setScriptReady] = useState(false);
  const [scriptFailed, setScriptFailed] = useState(false);
  const [message, setMessage] = useState("Complete the verification to continue.");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (
      !siteKey ||
      !scriptReady ||
      !containerRef.current ||
      !window.turnstile ||
      widgetIdRef.current
    )
      return;
    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: siteKey,
      action: "record_search_enforcement",
      callback: async (token) => {
        setSubmitting(true);
        setMessage("Verifying…");
        try {
          const response = await fetch("/records/search/challenge", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ token }),
          });
          const body = (await response.json()) as {
            verified?: boolean;
            status?: BrowserChallengeStatus;
          };
          const action = body.status ? challengeUiAction(body.status) : "RESET_UNAVAILABLE";
          if (action === "RELOAD") {
            window.location.reload();
            return;
          }
          setMessage(
            action === "RESET_UNAVAILABLE"
              ? "Verification is temporarily unavailable. Please try again."
              : "Verification was not accepted. Please try again.",
          );
          window.turnstile?.reset(widgetIdRef.current);
        } catch {
          setMessage("Verification is temporarily unavailable. Please try again.");
          window.turnstile?.reset(widgetIdRef.current);
        } finally {
          setSubmitting(false);
        }
      },
      "error-callback": () => setMessage("Verification failed. Please try again."),
      "expired-callback": () => setMessage("Verification expired. Please try again."),
    });
    return () => {
      removeTurnstileWidget(window.turnstile, widgetIdRef.current);
      widgetIdRef.current = undefined;
    };
  }, [scriptReady, siteKey]);

  if (!siteKey) {
    return <p className="text-sm text-amber-800">Verification is not configured.</p>;
  }

  return (
    <div className="space-y-4" aria-live="polite">
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
        strategy="afterInteractive"
        onLoad={() => setScriptReady(true)}
        onError={() => {
          setScriptFailed(true);
          setMessage("Verification is temporarily unavailable. Please try again.");
        }}
      />
      {!scriptFailed && <div ref={containerRef} />}
      <p className="text-sm text-slate-600">{submitting ? "Verifying…" : message}</p>
    </div>
  );
}
