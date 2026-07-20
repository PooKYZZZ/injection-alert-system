import { headers } from "next/headers";

const DEFAULT_ENDPOINT =
  "http://backend:8000/api/internal/enforcement/check";
const DEFAULT_TIMEOUT_MS = 250;

function firstForwardedAddress(value: string | null) {
  return value?.split(",", 1)[0]?.trim() || null;
}

export function requestSourceIp(requestHeaders: Headers) {
  return (
    requestHeaders.get("cf-connecting-ip") ||
    firstForwardedAddress(requestHeaders.get("x-forwarded-for")) ||
    requestHeaders.get("x-real-ip") ||
    null
  );
}

export async function checkRecordSearchShadowEnforcement(): Promise<void> {
  const apiKey = process.env.ENFORCEMENT_CHECK_API_KEY?.trim();
  const endpoint =
    process.env.ENFORCEMENT_CHECK_URL?.trim() || DEFAULT_ENDPOINT;
  if (!apiKey) return;

  const sourceIp = requestSourceIp(await headers());
  if (!sourceIp) return;

  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    Number(process.env.ENFORCEMENT_CHECK_TIMEOUT_MS) || DEFAULT_TIMEOUT_MS,
  );
  try {
    await fetch(endpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ scope: "RECORD_SEARCH", source_ip: sourceIp }),
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    // Shadow enforcement is observational. A backend timeout or outage must
    // never change the portal response or expose an implementation detail.
  } finally {
    clearTimeout(timeout);
  }
}
