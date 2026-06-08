// scripts/normal-requests.ts
// LOCAL LAB ONLY.
// Direct simulation script that generates safe, normal citizen traffic.
// Usage: npx tsx scripts/normal-requests.ts

export {};

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

async function sendGet(path: string) {
  const url = `${BASE_URL}${path}`;
  console.log(`Sending normal GET to: ${url}`);
  try {
    const res = await fetch(url);
    console.log(` -> Status: ${res.status} ${res.statusText}\n`);
  } catch (error) {
    console.error(` -> Failed to fetch ${url}:`, error, '\n');
  }
}

async function sendPost(path: string, urlEncodedBody: Record<string, string>) {
  const url = `${BASE_URL}${path}`;
  console.log(`Sending normal POST to: ${url}`);
  try {
    const body = new URLSearchParams(urlEncodedBody);
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
      redirect: 'manual', // We inspect redirect parameters manually
    });
    console.log(` -> Status: ${res.status} ${res.statusText}`);
    console.log(` -> Location Redirect Header: ${res.headers.get('location')}\n`);
  } catch (error) {
    console.error(` -> Failed to POST ${url}:`, error, '\n');
  }
}

async function runSimulation() {
  console.log('================================================================');
  console.log('         STARTING NORMAL TRAFFIC SIMULATION FOR WAF AUDITS      ');
  console.log(`         Target URL: ${BASE_URL}                                `);
  console.log('================================================================\n');

  // 1. Visit Portal Landing Page
  await sendGet('/');

  // 2. View Service Catalog
  await sendGet('/services');

  // 3. Search for existing records
  await sendGet('/records/search?query=Maple');

  // 4. View detailed layout of seeded record
  await sendGet('/records/LND-2026-0001');

  // 5. Look up standard transaction status tracking
  await sendGet('/transactions/status?ref=TXN-100201');

  // 6. View Public Comments
  await sendGet('/comments');

  // 7. Submit standard comment to the SQLite Database
  await sendPost('/comments/submit', {
    displayName: 'Maria Santos',
    message: 'I scheduled my property inspection yesterday and got an immediate confirmation code.',
  });

  // 8. Submit standard appointment form
  await sendPost('/appointments/submit', {
    fullName: 'Daniel Reyes',
    email: 'jane.smith@example.net',
    branch: 'Marikina Extension Desk',
    serviceType: 'Boundary Dispute Arbitration',
    preferredDate: '2026-06-20',
    notes: 'Please retrieve boundary coordinates files beforehand.',
  });

  // 9. Submit standard support dispute ticket
  await sendPost('/support/submit', {
    subject: 'Proposed Area Typo Correction',
    category: 'System Technical Error',
    email: 'george.p@example.com',
    referenceNo: 'LND-2026-0002',
    message: 'The total tract lot size says 450 sqm instead of 540 sqm. Please check registry deed of sale.',
  });

  // 10. Perform standard mock staff login
  await sendPost('/login/submit', {
    username: 'staff_auditor_a',
    password: 'DemoInteractiveSecurityPin789',
  });

  // 11. Request standard Certified True Copy (CTC)
  await sendPost('/records/LND-2026-0001/request-copy/submit', {
    fullName: 'Maria Santos',
    email: 'jane.smith@example.net',
    purpose: 'Mortgage Loan Verification',
    deliveryOption: 'Official Physical Stamp Copy',
    remarks: 'I will pick up the printed document from Marikina branch office next Tuesday.',
  });

  console.log('================================================================');
  console.log('         NORMAL SIMULATED TRAFFIC COMPLETED SUCCESSFULLY        ');
  console.log('================================================================');
}

runSimulation();
