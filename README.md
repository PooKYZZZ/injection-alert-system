# Land Records Demo Portal

A realistic, boring, and highly structured public-service citizen records registry website.

The app includes local demo routes, native HTML forms, and explicit route handlers so request flows are easy to inspect in a local lab setup.

---

## 🚀 Key Features Enclosed

* **Records Registry Directory:** Query indexed real-estate details with combinations of location and status filters.
* **Certified True Copy Application:** File structured requests against indexed items, creating tracked transactions with unique reference IDs.
* **Dispatch Timeline Tracker:** Stepper visualizations tracking processing, review, and dispatch states.
* **Direct Office Consult Agenda:** Schedule in-person desk slots at the configured branch offices.
* **Lodge Citizen Grievances:** Ticket system for public support requests and reference tracking.
* **Public Comments Board:** Dynamic forum to leave citizen feedback, persisted in SQLite.
* **Staff Login Gateway:** Simulated login. Real authentication is disabled.

---

## 🛠️ Tech Stack & Constraints

* **Framework:** Next.js (with App Router)
* **Language:** TypeScript
* **Styling:** Tailwind CSS v4
* **Database / ORM:** Prisma ORM with local **SQLite** persistence
* **Validations:** Zod schema validation
* **Form Submissions:** Standard HTML form bodies submit urlencoded content directly to explicit Next.js route handlers. No React Server Actions are used for the main form flow.

---

## 💾 Standard Setup & Run Guide

Follow these simple phases to build and run the target sandbox locally.

### 1. Install Node Dependencies
Use a current Node.js runtime compatible with Next.js 15.
```bash
npm install
```

### 2. Database Push and Seed
Generate the native SQLite schema on your local workspace and seed it with mock assets:
```bash
npx prisma db push
npx prisma db seed
```

### 3. Run Development Server
Spins up the interactive web console at [http://localhost:3000](http://localhost:3000):
```bash
npm run dev
```

### 4. Build Standalone Assets
Compiles production-optimized code and assets:
```bash
npm run build
npm start
```

---

## 🐳 Docker Deployment

The application compiles inside lightweight Alpine Docker containers using Next.js standalone server targets.

To compile and launch the container on desktop:
```bash
docker-compose up --build
```
The portal console opens at `http://localhost:3000`.

---

## 🛡️ Local Traffic Scripts

The `scripts/` directory contains two client scripts for local request inspection scenarios:

### Normal Public Traffic Generation
Polls search indices, reads details, files comments, and schedules appointments with valid inputs:
```bash
npx tsx scripts/normal-requests.ts
```

### Suspicious Local Lab Simulation
LOCAL LAB ONLY. Sends obvious SQL injection, path traversal, and cross-site scripting patterns against search parameters, comments, and login flows:
```bash
npx tsx scripts/suspicious-requests.ts
```

*For route and field mappings, see [docs/WAF_READY_ROUTES.md](./docs/WAF_READY_ROUTES.md).*
