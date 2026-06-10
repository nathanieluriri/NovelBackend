/** Lazy env access — never read env at module top level (breaks `next build`). */
export function env(name: string, fallback?: string): string | undefined {
  return process.env[name] ?? fallback;
}

export function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing required env var: ${name}`);
  return v;
}

export function envBool(name: string, fallback = true): boolean {
  const v = process.env[name];
  if (v === undefined || v === "") return fallback;
  return !["false", "0", "no", "off"].includes(v.toLowerCase());
}

export function envInt(name: string, fallback: number): number {
  const v = process.env[name];
  if (!v) return fallback;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? fallback : n;
}
