# Route Inventory - Land Records Portal

This document indexes the accessible routes, forms, and simulated endpoints available in the Land Records Demo Portal. These fields are intended for local inspection and anomaly scoring in a sandbox lab.

LOCAL LAB ONLY. Do not run against public or third-party systems.

---

## Technical Scope of Endpoints

| Method | Request URI / Route | Form Fields / Parameters | Target Service Handler | OWASP CRS Rule Scope | Test Vectors | Expected Sandbox Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GET** | `/records/search` | `query` (URL parameter) | `/app/records/search/page.tsx` | Query parameter validation | `' OR 1=1 --` | Returns filtered results or empty state. |
| **GET** | `/records/[recordNo]` | `recordNo` (Path variable) | `/app/records/[recordNo]/page.tsx` | Path normalization | `../../etc/passwd` | Renders a standard 404 if the record is unknown. |
| **GET** | `/transactions/status` | `ref` (URL parameter) | `/app/transactions/status/page.tsx` | Reference lookup handling | `SUP-2026-0001` or raw strings | Renders a status view mapped to stored demo records. |
| **POST** | `/support/submit` | `email`, `category`, `subject`, `message`, `referenceNo` | `/app/support/submit/route.ts` | Form body validation | `<script>alert(1)</script>` | 303 Redirect to success page after server validation and Prisma write. |
| **POST** | `/appointments/submit` | `fullName`, `email`, `branch`, `serviceType`, `preferredDate`, `notes` | `/app/appointments/submit/route.ts` | Form body validation | Large buffer streams | 303 Redirect after server validation and Prisma write. |
| **POST** | `/comments/submit` | `displayName`, `message` | `/app/comments/submit/route.ts` | Stored content handling | `displayName=<svg onload=confirm(1)>` | 303 Redirect after server validation and Prisma write. |
| **POST** | `/login/submit` | `username`, `password` | `/app/login/submit/route.ts` | Login form validation | `' OR '1'='1` | 303 Redirect after server validation and Prisma write. |
| **GET** | `/records/[recordNo]/request-copy` | `recordNo` (Path variable) | `/app/records/[recordNo]/request-copy/page.tsx` | Page retrieval | N/A | Renders an accessible form page. |
| **POST** | `/records/[recordNo]/request-copy/submit` | `fullName`, `email`, `purpose`, `deliveryOption`, `remarks` | `/app/records/[recordNo]/request-copy/submit/route.ts` | Request body validation | Tampered delivery parameters | 303 Redirect after server validation and Prisma write. |

---

## Test Vectors Guidelines

When setting up verification scripts for OWASP CRS inside your lab container:

1. **SQL Injection Vector (SQLi) Test:**
   ```bash
   curl -i -X GET "http://localhost:3000/records/search?query=%27%20UNION%20SELECT%20null,null,null,null,null,null--%20"
   ```
   *Expected local-lab observation:* query handling and output escaping remain stable.

2. **Cross-Site Scripting Vector (XSS) Test:**
   ```bash
   curl -i -X POST "http://localhost:3000/comments/submit" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "displayName=%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E&message=ComplianceTest"
   ```
   *Expected local-lab observation:* stored content is handled safely and then persisted.

3. **Inbound Metadata Telemetry Test:**
   ```bash
   curl -i -X GET "http://localhost:3000/transactions/status?ref=SUP-2026-0001" \
     -H "x-demo-trace-id: tr-compliance-998x"
   ```
   *Expected portal action:* reads the trace ID header and displays it within simulated response layouts to aid local inspection.
