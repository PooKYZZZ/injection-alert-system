import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { prisma } from "../lib/prisma";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";
const BASE_PORT = new URL(BASE_URL).port || "3000";

type ModelCounts = {
  Record: number;
  Transaction: number;
  SupportTicket: number;
  Appointment: number;
  Comment: number;
  LoginAttempt: number;
};

type CheckResult = Record<string, unknown>;

const evidence: {
  base_url: string;
  database: CheckResult;
  counts_before: ModelCounts | null;
  counts_after: ModelCounts | null;
  get_routes: CheckResult[];
  form_submission_results: CheckResult[];
  validation_results: CheckResult[];
  suspicious_value_results: CheckResult[];
  status_lookup_results: CheckResult[];
  cookie_findings: CheckResult[];
} = {
  base_url: BASE_URL,
  database: {},
  counts_before: null,
  counts_after: null,
  get_routes: [],
  form_submission_results: [],
  validation_results: [],
  suspicious_value_results: [],
  status_lookup_results: [],
  cookie_findings: [],
};

async function counts(): Promise<ModelCounts> {
  const [record, transaction, supportTicket, appointment, comment, loginAttempt] = await Promise.all([
    prisma.record.count(),
    prisma.transaction.count(),
    prisma.supportTicket.count(),
    prisma.appointment.count(),
    prisma.comment.count(),
    prisma.loginAttempt.count(),
  ]);

  return {
    Record: record,
    Transaction: transaction,
    SupportTicket: supportTicket,
    Appointment: appointment,
    Comment: comment,
    LoginAttempt: loginAttempt,
  };
}

async function request(path: string, init?: RequestInit) {
  return fetch(`${BASE_URL}${path}`, {
    redirect: "manual",
    ...init,
    headers: {
      "x-demo-trace-id": "backend-readiness-audit",
      ...(init?.headers ?? {}),
    },
  });
}

function form(fields: Record<string, string>) {
  return new URLSearchParams(fields);
}

async function textIncludes(response: Response, expected: string) {
  const body = await response.text();
  return body.includes(expected);
}

async function waitForServer() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await request("/");
      if (response.ok) return;
    } catch {
      // Retry until the dev server finishes booting.
    }
    await delay(1000);
  }
  throw new Error("Local app did not become ready");
}

async function main() {
  evidence.database = {
    database_url: process.env.DATABASE_URL ?? null,
    sqlite_path: resolve("prisma/dev.db"),
    sqlite_exists: existsSync(resolve("prisma/dev.db")),
  };

  evidence.counts_before = await counts();

  let devServer: ReturnType<typeof spawn> | null = null;
  const shouldStartServer = process.env.SKIP_START !== "1";
  if (shouldStartServer) {
    devServer = spawn("npx", ["next", "dev", "-p", BASE_PORT],
    {
      shell: true,
      stdio: "ignore",
      env: { ...process.env, PORT: BASE_PORT },
    });
  }

  try {
    await waitForServer();

    const getChecks = [
      ["/", "Land"],
      ["/records/search", "Search"],
      ["/records/search?query=LND-2026-0001", "LND-2026-0001"],
      ["/transactions/status", "Registry Status"],
      ["/transactions/status?ref=TXN-2026-0001", "Registry Status"],
      ["/support", "Support"],
      ["/appointments", "Appointment"],
      ["/comments", "Comments"],
      ["/login", "Demo"],
      ["/records/LND-2026-0001", "LND-2026-0001"],
      ["/records/LND-2026-0001/request-copy", "Certified"],
      ["/services", "Services"],
      ["/success", "Success"],
      ["/demo-guide", "Demo"],
    ] as const;

    for (const [path, expected] of getChecks) {
      const response = await request(path);
      evidence.get_routes.push({
        path,
        status: response.status,
        redirect: response.status >= 300 && response.status < 400,
        content_sanity: await textIncludes(response, expected),
      });
    }

    const formChecks = [
      {
        flow: "Support ticket",
        path: "/support/submit",
        model: "SupportTicket",
        body: form({
          email: "audit-support@example.com",
          category: "General Inquiry",
          subject: "Backend readiness audit support ticket",
          referenceNo: "AUDIT-CLIENT-REF",
          message: "Normal local audit support message.",
        }),
      },
      {
        flow: "Appointment",
        path: "/appointments/submit",
        model: "Appointment",
        body: form({
          fullName: "Backend Audit User",
          email: "audit-appointment@example.com",
          branch: "North District Registry",
          serviceType: "Record Consultation",
          preferredDate: "2026-06-10",
          notes: "Normal local audit appointment.",
        }),
      },
      {
        flow: "Comment",
        path: "/comments/submit",
        model: "Comment",
        body: form({
          displayName: "Backend Audit Commenter",
          message: "Normal local audit comment for SQLite persistence.",
        }),
      },
      {
        flow: "Demo login",
        path: "/login/submit",
        model: "LoginAttempt",
        body: form({
          username: "backend-audit-user",
          password: "not-stored-audit-password",
        }),
      },
      {
        flow: "Certified copy request",
        path: "/records/LND-2026-0001/request-copy/submit",
        model: "Transaction",
        body: form({
          fullName: "Backend Audit Requester",
          email: "audit-copy@example.com",
          purpose: "Backend readiness audit",
          deliveryOption: "Email (Digital Copy)",
          remarks: "Normal local audit copy request.",
        }),
      },
    ] as const;

    for (const check of formChecks) {
      const before = await counts();
      const response = await request(check.path, {
        method: "POST",
        body: check.body,
        headers: { "content-type": "application/x-www-form-urlencoded" },
      });
      const after = await counts();
      const location = response.headers.get("location");
      const setCookie = response.headers.get("set-cookie");
      const ref = location ? new URL(location, BASE_URL).searchParams.get("ref") : null;
      evidence.form_submission_results.push({
        flow: check.flow,
        path: check.path,
        response_status: response.status,
        redirect_location: location,
        set_cookie: setCookie,
        count_before: before[check.model],
        count_after: after[check.model],
        db_write_verified: after[check.model] === before[check.model] + 1,
        generated_reference: ref,
      });
      evidence.cookie_findings.push({ flow: check.flow, set_cookie: setCookie });
    }

    const validationChecks = [
      {
        case: "Missing required support field",
        path: "/support/submit",
        body: form({ email: "audit@example.com", category: "", subject: "", referenceNo: "", message: "" }),
      },
      {
        case: "Invalid email",
        path: "/support/submit",
        body: form({ email: "not-an-email", category: "General Inquiry", subject: "Invalid email audit", referenceNo: "", message: "Normal length message" }),
      },
      {
        case: "Past appointment date",
        path: "/appointments/submit",
        body: form({ fullName: "Past Date User", email: "past@example.com", branch: "North District Registry", serviceType: "Record Consultation", preferredDate: "2020-01-01", notes: "" }),
      },
      {
        case: "Missing login username",
        path: "/login/submit",
        body: form({ username: "", password: "password-present" }),
      },
      {
        case: "Missing copy request purpose",
        path: "/records/LND-2026-0001/request-copy/submit",
        body: form({ fullName: "Copy User", email: "copy@example.com", purpose: "", deliveryOption: "Email (Digital Copy)", remarks: "" }),
      },
      {
        case: "Nonexistent record number for request-copy",
        path: "/records/DOES-NOT-EXIST/request-copy/submit",
        body: form({ fullName: "Copy User", email: "copy@example.com", purpose: "Audit", deliveryOption: "Email (Digital Copy)", remarks: "" }),
      },
      {
        case: "Nonexistent transaction reference",
        path: "/transactions/status?ref=DOES-NOT-EXIST",
        body: null,
      },
    ] as const;

    for (const check of validationChecks) {
      const before = await counts();
      const response = check.body
        ? await request(check.path, { method: "POST", body: check.body, headers: { "content-type": "application/x-www-form-urlencoded" } })
        : await request(check.path);
      const body = await response.text();
      const after = await counts();
      evidence.validation_results.push({
        case: check.case,
        path: check.path,
        status: response.status,
        no_db_row_created: JSON.stringify(before) === JSON.stringify(after),
        stack_trace_leaked: body.includes("Error:") || body.includes(" at "),
        body_excerpt: body.replace(/\s+/g, " ").slice(0, 180),
      });
    }

    const suspicious = "<script>alert('audit')</script>";
    const suspiciousChecks = [
      { field: "Search query route", path: `/records/search?query=${encodeURIComponent(suspicious)}`, method: "GET" as const },
      { field: "Support message field", path: "/support/submit", method: "POST" as const, body: form({ email: "audit-suspicious-support@example.com", category: "General Inquiry", subject: "Suspicious value audit", referenceNo: "", message: suspicious }) },
      { field: "Comment message field", path: "/comments/submit", method: "POST" as const, body: form({ displayName: "Suspicious Audit", message: suspicious }) },
      { field: "Copy request remarks field", path: "/records/LND-2026-0001/request-copy/submit", method: "POST" as const, body: form({ fullName: "Suspicious Copy User", email: "audit-suspicious-copy@example.com", purpose: "Audit", deliveryOption: "Email (Digital Copy)", remarks: suspicious }) },
      { field: "Login username field", path: "/login/submit", method: "POST" as const, body: form({ username: suspicious, password: "not-stored-audit-password" }) },
    ];

    for (const check of suspiciousChecks) {
      const before = await counts();
      const response = await request(check.path, check.method === "POST"
        ? { method: "POST", body: check.body, headers: { "content-type": "application/x-www-form-urlencoded" } }
        : undefined);
      const after = await counts();
      const location = response.headers.get("location");
      evidence.suspicious_value_results.push({
        field: check.field,
        path: check.path,
        status: response.status,
        redirect_location: location,
        db_write_behavior: JSON.stringify(before) === JSON.stringify(after) ? "no-write" : "write",
        crashed: response.status >= 500,
      });
    }

    for (const submitted of evidence.form_submission_results) {
      const ref = submitted.generated_reference;
      if (typeof ref === "string" && ref) {
        const response = await request(`/transactions/status?ref=${encodeURIComponent(ref)}`);
        const body = await response.text();
        evidence.status_lookup_results.push({
          flow: submitted.flow,
          reference: ref,
          status: response.status,
          found: body.includes(ref),
          body_has_status_page: body.includes("Registry Status"),
        });
      }
    }

    evidence.counts_after = await counts();
  } finally {
    if (devServer) {
      devServer.kill();
    }
    await prisma.$disconnect();
  }

  console.log(JSON.stringify(evidence, null, 2));
}

main().catch(async (error) => {
  console.error(error);
  await prisma.$disconnect();
  process.exit(1);
});
