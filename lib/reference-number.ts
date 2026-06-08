/**
 * Generates unified reference tokens for sandbox operations.
 * These prefix codes help associate transactions with demo trace IDs and history items.
 */
export function generateReferenceNumber(prefix: "SUP" | "APT" | "REQ" | "TXN" | string): string {
  const year = 2026;
  const sequence = Math.floor(1000 + Math.random() * 9000);
  return `${prefix.toUpperCase()}-${year}-${sequence}`;
}
