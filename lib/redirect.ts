import { NextRequest, NextResponse } from "next/server";

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);
const DOCKER_INTERNAL_HOSTS = new Set(["portal", "web", "app"]);

function firstHeaderValue(value: string | null): string | null {
  return value?.split(",")[0]?.trim() || null;
}

function normalizeHost(host: string | null, fallbackUrl: string): string {
  const fallbackHost = new URL(fallbackUrl).host;
  const rawHost = host || fallbackHost;
  const hostname = rawHost.split(":")[0]?.toLowerCase();

  if (!hostname || hostname === "0.0.0.0" || DOCKER_INTERNAL_HOSTS.has(hostname)) {
    const fallbackPort = rawHost.includes(":") ? rawHost.split(":").slice(1).join(":") : "3000";
    return `localhost${fallbackPort ? `:${fallbackPort}` : ""}`;
  }

  return rawHost.replace(/^0\.0\.0\.0(?=:|$)/, "localhost");
}

function protocolForHost(host: string, forwardedProto: string | null): string {
  const hostname = host.split(":")[0]?.toLowerCase();

  if (hostname && LOCAL_HOSTS.has(hostname)) {
    return "http";
  }

  return forwardedProto || "https";
}

export function browserRedirect(request: NextRequest, path: string): NextResponse {
  const forwardedHost = firstHeaderValue(request.headers.get("x-forwarded-host"));
  const host = normalizeHost(forwardedHost || request.headers.get("host"), request.url);
  const forwardedProto = firstHeaderValue(request.headers.get("x-forwarded-proto"));
  const protocol = protocolForHost(host, forwardedProto);
  const url = new URL(path, `${protocol}://${host}`);

  return NextResponse.redirect(url, 303);
}
