// scripts/suspicious-requests.ts
// LOCAL LAB ONLY.
// Direct simulation script that generates obvious, signature-rich test payloads.
// Usage: npx tsx scripts/suspicious-requests.ts

export {};

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

async function sendSuspiciousGet(description: string, queryPath: string) {
  const url = `${BASE_URL}${queryPath}`;
  console.log(`[TEST] (${description})`);
  console.log(`       GET: ${url}`);
  try {
    const res = await fetch(url);
    console.log(`       -> Response Code: ${res.status} ${res.statusText}`);
    if (res.status === 403 || res.status === 406) {
      console.log('       -> STATUS: inspection layer likely flagged the pattern\n');
    } else {
      console.log('       -> STATUS: request was accepted by the app route\n');
    }
  } catch (error) {
    console.error(`       -> Connection Error:`, error, '\n');
  }
}

async function sendSuspiciousPost(description: string, path: string, urlEncodedBody: Record<string, string>) {
  const url = `${BASE_URL}${path}`;
  console.log(`[TEST] (${description})`);
  console.log(`       POST: ${url}`);
  try {
    const body = new URLSearchParams(urlEncodedBody);
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body,
      redirect: 'manual',
    });
    console.log(`       -> Response Code: ${res.status} ${res.statusText}`);
    if (res.status === 403 || res.status === 406) {
      console.log('       -> STATUS: inspection layer likely flagged the pattern\n');
    } else {
      console.log('       -> STATUS: request was accepted by the app route\n');
    }
  } catch (error) {
    console.error(`       -> Connection Error:`, error, '\n');
  }
}

async function runAttackSimulation() {
  console.log('================================================================');
  console.log('         !!! FOR LOCAL LAB USE ONLY - PROMPT TESTING !!!        ');
  console.log('         STARTING SUSPICIOUS TRAFFIC SIMULATION                ');
  console.log(`         Target URL: ${BASE_URL}                                `);
  console.log('================================================================\n');

  // Test 1: Simple SQL Injection (SQLi) in Search Query GET Parameter
  // Looking to trigger Core Rule Set SQLi Injection Rules (e.g., Rule 942100)
  await sendSuspiciousGet(
    'SQLi Tautology in Search',
    "/records/search?query=%27+OR+1%3D1+--"
  );

  // Test 2: Cross-Site Scripting (XSS) in Status Lookup GET Parameter
  // Looking to trigger XSS Detection Rules (e.g., Rule 941100)
  await sendSuspiciousGet(
    'XSS script tag in status tracker',
    "/transactions/status?ref=%3Cscript%3Ealert%281%29%3C%2Fscript%3E"
  );

  // Test 3: Local File Inclusion / Path Traversal in Record Parameter
  // Looking to trigger Path Traversal Rules (e.g., Rule 930110)
  await sendSuspiciousGet(
    'Path Traversal in Dynamic Record path',
    "/records/..%2f..%2f..%2f..%2fetc%2fpasswd"
  );

  // Test 4: Login form validation with suspicious body data
  await sendSuspiciousPost(
    'Suspicious login username form',
    '/login/submit',
    {
      username: "' OR '1'='1",
      password: "password123"
    }
  );

  // Test 5: Cross-Site Scripting (XSS) payload inside comment body POST
  // Looking to trigger persistent XSS payload capture
  await sendSuspiciousPost(
    'XSS HTML tag inside Comment text field',
    '/comments/submit',
    {
      displayName: 'Malicious Guest',
      message: '<img src=x onerror=alert(document.cookie)>'
    }
  );

  // Test 6: XSS pattern in certified copy application remarks
  await sendSuspiciousPost(
    'XSS pattern in certified copy remarks',
    '/records/LND-2026-0001/request-copy/submit',
    {
      fullName: 'Security Auditor',
      email: 'auditor@cybertrace.local',
      purpose: 'Verification',
      deliveryOption: 'Local Pickup',
      remarks: '<script>alert(document.domain)</script>'
    }
  );

  console.log('================================================================');
  console.log('         SUSPICIOUS PENETRATION SIGNATURE SIMULATION COMPLETE   ');
  console.log('================================================================');
}

runAttackSimulation();
