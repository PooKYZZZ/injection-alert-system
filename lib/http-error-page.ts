export type HttpErrorStatus = 403 | 404 | 429 | 500 | 502 | 503 | 504;

type HttpErrorPageCopy = {
  title: string;
  message: string;
  icon: "shield" | "clock" | "search" | "server";
  action: "home" | "retry";
  actionLabel: string;
  supportLink?: boolean;
};

const ERROR_PAGE_COPY: Record<HttpErrorStatus, HttpErrorPageCopy> = {
  403: {
    title: "Access Restricted",
    message: "We couldn't complete your request because access was restricted.",
    icon: "shield",
    action: "home",
    actionLabel: "Return to Homepage",
    supportLink: true,
  },
  404: {
    title: "Page Not Found",
    message: "The page you're looking for might have been moved or no longer exists.",
    icon: "search",
    action: "home",
    actionLabel: "Back to Homepage",
  },
  429: {
    title: "Too Many Requests",
    message:
      "You've made too many requests in a short period. Please wait before trying again.",
    icon: "clock",
    action: "home",
    actionLabel: "Return to Homepage",
  },
  500: {
    title: "Server Error",
    message:
      "We're having trouble processing your request right now. Please try again later.",
    icon: "server",
    action: "retry",
    actionLabel: "Try Again",
  },
  502: {
    title: "Service Unavailable",
    message: "We couldn't reach the service right now. Please try again in a moment.",
    icon: "server",
    action: "retry",
    actionLabel: "Try Again",
  },
  503: {
    title: "Temporarily Unavailable",
    message:
      "We're having trouble processing requests right now. Please try again later.",
    icon: "server",
    action: "retry",
    actionLabel: "Try Again",
  },
  504: {
    title: "Request Timed Out",
    message: "The service took too long to respond. Please try again later.",
    icon: "clock",
    action: "retry",
    actionLabel: "Try Again",
  },
};

const ERROR_PAGE_STYLES = `
:root {
  color-scheme: dark;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  color: #f8fafc;
  background: #0c141e;
}
* { box-sizing: border-box; }
html, body { min-height: 100%; margin: 0; }
body { background: #0c141e; color: #f8fafc; }
.http-error-screen {
  min-height: 70vh;
  display: grid;
  place-items: center;
  padding: 20px;
  background: #0c141e;
  color: #f8fafc;
}
body.http-error-standalone .http-error-screen { min-height: 100vh; }
.http-error-card {
  width: min(100%, 760px);
  overflow: hidden;
  border: 1px solid #293747;
  border-radius: 12px;
  background: #151e28;
  box-shadow: 0 18px 50px #0004;
}
.http-error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #2b3949;
}
.http-error-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #f1f5f9;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
}
.http-error-brand svg { width: 16px; height: 16px; color: #8bd4ff; }
.http-error-status {
  padding: 4px 8px;
  border-radius: 7px;
  background: #2b3644;
  color: #e2e8f0;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
}
.http-error-content { padding: 28px 20px 34px; text-align: center; }
.http-error-icon {
  display: block;
  width: 28px;
  height: 28px;
  margin: 0 auto 12px;
  color: #f3ad28;
}
.http-error-icon--info { color: #79c9f6; }
.http-error-content h1 {
  margin: 0;
  color: #f8fafc;
  font-size: clamp(22px, 4vw, 28px);
  font-weight: 700;
  line-height: 1.2;
}
.http-error-message {
  margin: 10px auto 18px;
  color: #cbd5e1;
  font-size: 15px;
  line-height: 1.55;
}
.http-error-retry {
  margin: -6px auto 16px;
  color: #93a4b8;
  font-size: 13px;
  line-height: 1.5;
}
.http-error-support { margin: 16px 0 0; color: #93a4b8; font-size: 13px; }
.http-error-support a { color: #a8dfff; }
.http-error-action {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #eaf2ff;
  padding: 8px 14px;
  color: #0f172a;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
}
.http-error-action:hover { background: #dbeafe; }
.http-error-action:focus-visible { outline: 3px solid #7dd3fc; outline-offset: 3px; }
@media (max-width: 480px) {
  .http-error-screen { padding: 12px; }
  .http-error-header { padding: 12px; }
  .http-error-content { padding: 24px 16px 28px; }
  .http-error-message { font-size: 14px; }
}
`;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function iconMarkup(icon: HttpErrorPageCopy["icon"]): string {
  switch (icon) {
    case "shield":
      return '<path d="M12 3 20 6v5c0 5-3.3 8.2-8 10-4.7-1.8-8-5-8-10V6l8-3Z"/><path d="M12 8v5m0 3h.01"/>';
    case "clock":
      return '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2m4-9 2-2"/>';
    case "search":
      return '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M8 8l5 5m0-5-5 5"/>';
    case "server":
      return '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01M12 6v2m0 8v2"/>';
  }
}

export function httpErrorPageMarkup(
  status: HttpErrorStatus,
  retryAfterSeconds?: number,
): string {
  const copy = ERROR_PAGE_COPY[status];
  const retryNote =
    status === 429 &&
    retryAfterSeconds !== undefined &&
    Number.isSafeInteger(retryAfterSeconds) &&
    retryAfterSeconds >= 0
      ? `<p class="http-error-retry">Retry after ${retryAfterSeconds} seconds.</p>`
      : "";
  const action =
    copy.action === "retry"
      ? `<form action="" method="get"><button class="http-error-action" type="submit">${escapeHtml(copy.actionLabel)}</button></form>`
      : `<a class="http-error-action" href="/">${escapeHtml(copy.actionLabel)}</a>`;
  const supportLink = copy.supportLink
    ? '<p class="http-error-support">Need help? <a href="/support">Contact Support</a>.</p>'
    : "";

  return `
    <style>${ERROR_PAGE_STYLES}</style>
    <section class="http-error-screen" aria-label="HTTP error">
      <article class="http-error-card" aria-labelledby="http-error-title">
        <header class="http-error-header">
          <a class="http-error-brand" href="/" aria-label="Land Records Portal home">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="M12 3 20 6v5c0 5-3.3 8.2-8 10-4.7-1.8-8-5-8-10V6l8-3Z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
            <span>Land Records Portal</span>
          </a>
          <span class="http-error-status" aria-label="HTTP ${status}">${status}</span>
        </header>
        <div class="http-error-content">
          <svg class="http-error-icon ${status === 404 ? "http-error-icon--info" : ""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            ${iconMarkup(copy.icon)}
          </svg>
          <h1 id="http-error-title">${escapeHtml(copy.title)}</h1>
          <p class="http-error-message">${escapeHtml(copy.message)}</p>
          ${retryNote}
          ${action}
          ${supportLink}
        </div>
      </article>
    </section>
  `;
}

export function httpErrorPageDocument(
  status: HttpErrorStatus,
  retryAfterSeconds?: number,
): string {
  const title = escapeHtml(ERROR_PAGE_COPY[status].title);
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="dark">
    <meta name="referrer" content="no-referrer">
    <title>${title}</title>
  </head>
  <body class="http-error-standalone">
    <main id="main-content">${httpErrorPageMarkup(status, retryAfterSeconds)}</main>
  </body>
</html>`;
}
