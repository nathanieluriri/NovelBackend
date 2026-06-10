/**
 * Ensure all MongoDB indexes match the schema declarations.
 *
 * Models set `autoIndex: false`, so indexes are created here (one-off /
 * deploy-time), never at runtime. `syncIndexes()` creates missing indexes and
 * drops ones no longer declared in the schema.
 *
 * Run: npx tsx scripts/ensure-indexes.ts
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import mongoose from "mongoose";
import { db } from "../lib/db";
import {
  User,
  Admin,
  AllowedAdmin,
  Book,
  Chapter,
  Page,
  Like,
  Bookmark,
  Comment,
  Reaction,
  AuthorRoom,
  ReadingProgress,
  ReadRecord,
  Entitlement,
  PaymentBundle,
  PaymentRuntime,
  WebhookEvent,
  Transaction,
  AccessToken,
  RefreshToken,
  GoogleOAuthExchange,
  LoginAttempt,
} from "../lib/models";

/** Minimal .env loader (scripts run outside Next, which normally loads these). */
function loadEnvFiles(): void {
  for (const name of [".env.local", ".env"]) {
    const p = resolve(process.cwd(), name);
    if (!existsSync(p)) continue;
    for (const line of readFileSync(p, "utf8").split(/\r?\n/)) {
      const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
      if (!m) continue;
      let value = m[2];
      if (
        (value.startsWith('"') && value.endsWith('"') && value.length >= 2) ||
        (value.startsWith("'") && value.endsWith("'") && value.length >= 2)
      ) {
        value = value.slice(1, -1);
      }
      if (process.env[m[1]] === undefined) process.env[m[1]] = value;
    }
  }
}

const allModels: mongoose.Model<Record<string, any>>[] = [
  User,
  Admin,
  AllowedAdmin,
  Book,
  Chapter,
  Page,
  Like,
  Bookmark,
  Comment,
  Reaction,
  AuthorRoom,
  ReadingProgress,
  ReadRecord,
  Entitlement,
  PaymentBundle,
  PaymentRuntime,
  WebhookEvent,
  Transaction,
  AccessToken,
  RefreshToken,
  GoogleOAuthExchange,
  LoginAttempt,
];

async function main(): Promise<void> {
  loadEnvFiles();
  await db();

  for (const m of allModels) {
    try {
      const dropped = await m.syncIndexes();
      const indexes = await m.listIndexes();
      const names = indexes.map((ix: { name?: string }) => ix.name).join(", ");
      console.log(
        `[ensure-indexes] ${m.modelName} -> "${m.collection.name}": ok` +
          (dropped.length ? ` | dropped: [${dropped.join(", ")}]` : "") +
          ` | indexes: [${names}]`,
      );
    } catch (err) {
      console.error(`[ensure-indexes] ${m.modelName} -> "${m.collection.name}": FAILED`, err);
      process.exitCode = 1;
    }
  }

  await mongoose.disconnect();
  console.log("[ensure-indexes] done");
}

main().catch((err) => {
  console.error("[ensure-indexes] fatal:", err);
  process.exit(1);
});
