"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";

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
    };
  }
}

export function EnforcementChallenge({ siteKey }: { siteKey: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | undefined>(undefined);
  const [scriptReady, setScriptReady] = useState(false);
  const [message, setMessage] = useState("Complete the verification to continue.");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!siteKey || !scriptReady || !containerRef.current || !window.turnstile) return;
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
            status?: string;
          };
          if (body.verified === true && body.status === "VERIFIED") {
            window.location.reload();
            return;
          }
          setMessage(
            body.status === "UNAVAILABLE"
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
      />
      <div ref={containerRef} />
      <p className="text-sm text-slate-600">{submitting ? "Verifying…" : message}</p>
    </div>
  );
}
