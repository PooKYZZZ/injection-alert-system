'use client';

import { useRef, useState, type FormEvent } from 'react';
import { AlertCircle } from 'lucide-react';

type LoginIssue = {
  field?: 'username' | 'password';
  message: string;
};

export default function DemoLoginForm() {
  const [issues, setIssues] = useState<LoginIssue[]>([]);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const summaryRef = useRef<HTMLDivElement>(null);
  const successRef = useRef<HTMLDivElement>(null);

  const focusSummary = () => {
    window.setTimeout(() => {
      summaryRef.current?.focus();
      summaryRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSubmitting) return;

    const form = event.currentTarget;
    const formData = new FormData(form);
    const username = String(formData.get('username') || '');
    const password = String(formData.get('password') || '');
    const newIssues: LoginIssue[] = [];
    const newFieldErrors: Record<string, string> = {};

    if (!username) {
      const message = 'Enter a synthetic username.';
      newIssues.push({ field: 'username', message });
      newFieldErrors.username = message;
    }
    if (!password) {
      const message = 'Enter any test password. This form does not sign you in.';
      newIssues.push({ field: 'password', message });
      newFieldErrors.password = message;
    }

    if (newIssues.length > 0) {
      setSuccess(false);
      setIssues(newIssues);
      setFieldErrors(newFieldErrors);
      focusSummary();
      return;
    }

    setIssues([]);
    setFieldErrors({});
    setSuccess(false);
    setIsSubmitting(true);

    try {
      const payload = new URLSearchParams();
      payload.set('username', username);
      payload.set('password', password);

      const response = await fetch(form.action, {
        method: form.method.toUpperCase(),
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        body: payload.toString(),
        credentials: 'same-origin',
      });

      const responseUrl = new URL(response.url);
      if (
        response.ok &&
        response.redirected &&
        responseUrl.origin === window.location.origin &&
        responseUrl.pathname === '/success' &&
        responseUrl.searchParams.get('type') === 'login'
      ) {
        setSuccess(true);
        window.setTimeout(() => successRef.current?.focus(), 50);
        return;
      }

      let message = 'The demo login could not be processed. Please try again.';
      let responseError: string | undefined;
      if (response.headers.get('content-type')?.includes('application/json')) {
        const responseBody: unknown = await response.json().catch(() => null);
        if (
          responseBody &&
          typeof responseBody === 'object' &&
          'error' in responseBody &&
          typeof responseBody.error === 'string'
        ) {
          responseError = responseBody.error;
        }
      }

      if (response.status === 400) {
        message = responseError === 'Invalid input'
          ? 'The demo rejected those values. Check the username and password, then try again.'
          : 'The demo could not accept those values. Check the fields and try again.';
      } else if (response.status === 403 || response.status === 429) {
        message = 'This demo request is temporarily restricted. Wait a moment and try again.';
      } else if (response.status >= 500) {
        message = 'The demo login is temporarily unavailable. Try again later.';
      }

      setIssues([{ message }]);
      focusSummary();
    } catch {
      setIssues([{ message: 'The demo login could not be reached. Check your connection and try again.' }]);
      focusSummary();
    } finally {
      const passwordInput = form.querySelector<HTMLInputElement>('[name="password"]');
      if (passwordInput) passwordInput.value = '';
      setIsSubmitting(false);
    }
  };

  const clearIssues = () => {
    setIssues([]);
    setFieldErrors({});
    setSuccess(false);
  };

  return (
    <form
      action="/login/submit"
      method="post"
      onSubmit={handleSubmit}
      className="space-y-5 px-4 py-6 sm:px-6"
      noValidate
      aria-busy={isSubmitting}
    >
      {success && (
        <div
          id="login-success-feedback"
          ref={successRef}
          tabIndex={-1}
          role="status"
          className="mx-4 mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950 focus:outline-none focus:ring-2 focus:ring-emerald-600 sm:mx-6"
        >
          <h2 className="font-bold">Demo login attempt recorded</h2>
          <p className="mt-1 text-xs leading-relaxed">
            Authentication is disabled. No account or session was created.
          </p>
        </div>
      )}

      {issues.length > 0 && (
        <div
          id="login-errors-summary"
          ref={summaryRef}
          tabIndex={-1}
          role="alert"
          aria-labelledby="login-errors-heading"
          className="rounded-lg border border-red-200 bg-red-50 p-4 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden="true" />
            <div>
              <h2 id="login-errors-heading" className="text-xs font-bold uppercase tracking-wider text-red-950">
                Demo login not completed
              </h2>
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-red-800">
                {issues.map((issue, index) => (
                  <li key={`${issue.field || 'form'}-${index}`}>
                    {issue.field ? (
                      <a
                        className="underline underline-offset-2 hover:text-red-950 focus:outline-none focus:ring-2 focus:ring-red-500"
                        href={`#login-${issue.field}`}
                      >
                        {issue.message}
                      </a>
                    ) : (
                      issue.message
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        <label htmlFor="login-username" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
          Username <span aria-hidden="true" className="text-rose-600">*</span>
        </label>
        <input
          id="login-username"
          name="username"
          type="text"
          autoComplete="off"
          required
          aria-required="true"
          aria-invalid={Boolean(fieldErrors.username)}
          aria-describedby={fieldErrors.username ? 'login-username-error' : 'login-username-help'}
          onChange={clearIssues}
          className={`min-h-11 w-full rounded-lg border px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 ${
            fieldErrors.username ? 'border-red-500 focus:ring-red-500' : 'border-slate-300 focus:ring-blue-600'
          }`}
        />
        {fieldErrors.username ? (
          <p id="login-username-error" className="mt-1 text-xs font-medium text-red-700">{fieldErrors.username}</p>
        ) : (
          <p id="login-username-help" className="mt-1 text-xs text-slate-600">Use a synthetic test value.</p>
        )}
      </div>

      <div className="space-y-1.5">
        <label htmlFor="login-password" className="block text-xs font-bold uppercase tracking-wider text-slate-600">
          Password <span aria-hidden="true" className="text-rose-600">*</span>
        </label>
        <input
          id="login-password"
          name="password"
          type="password"
          autoComplete="off"
          required
          aria-required="true"
          aria-invalid={Boolean(fieldErrors.password)}
          aria-describedby={fieldErrors.password ? 'login-password-error' : 'login-password-help'}
          onChange={clearIssues}
          className={`min-h-11 w-full rounded-lg border px-3 py-2 text-sm text-slate-900 outline-none ring-offset-2 focus:ring-2 ${
            fieldErrors.password ? 'border-red-500 focus:ring-red-500' : 'border-slate-300 focus:ring-blue-600'
          }`}
        />
        {fieldErrors.password ? (
          <p id="login-password-error" className="mt-1 text-xs font-medium text-red-700">{fieldErrors.password}</p>
        ) : (
          <p id="login-password-help" className="mt-1 text-xs text-slate-600">Any synthetic value is accepted for this test flow.</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="min-h-11 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-bold text-white transition-colors hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:cursor-wait disabled:opacity-70"
      >
        {isSubmitting ? 'Sending test request…' : 'Submit demo attempt'}
      </button>
    </form>
  );
}
